import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import math
import scipy.interpolate
import pandas as pd
import numpy as np
import matplotlib
import slope
import unicodedata

CM_SERIF_FALLBACK = [
    "CMU Serif",
    "Latin Modern Roman",
    "Computer Modern Roman",
    "DejaVu Serif",
]


def _truncate_legend(text: str, max_chars: int) -> str:
    txt = str(text or "").replace("\n", " ").strip()
    if len(txt) <= max_chars:
        return txt
    return txt[: max(1, max_chars - 1)].rstrip() + "…"


def _escape_tex_text(text):
    raw = str(text)
    kept = []
    for ch in raw:
        cat = unicodedata.category(ch)
        if cat.startswith("C"):  # control chars
            continue
        # Symbol classes (e.g. arrows) often fail in plain LaTeX text mode.
        if cat.startswith("S") and ch not in "$":
            kept.append(" ")
            continue
        kept.append(ch)
    txt = "".join(kept)
    table = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(table.get(ch, ch) for ch in txt)

def _epoch_axis(df, fromyearmonth, stride):
    if stride is None:
        stride = max(1, int(len(df) / 25))

    if "epoch" in df.columns:
        epoch_labels = [str(x) for x in df["epoch"].tolist()]
    else:
        epoch_labels = [str(x) for x in list(df.index)]

    xsorig = np.arange(len(epoch_labels), dtype=float)

    # If we don't have explicit epoch labels (legacy numeric epochs), fall back to
    # generating YYYY-MM labels from `fromyearmonth`.
    if all(l.isdigit() for l in epoch_labels):
        tick_pos, tick_lab = label_years(fromyearmonth, nepochs=len(epoch_labels), stride=stride)
        tick_pos = np.array(tick_pos, dtype=float)
        tick_lab = list(tick_lab)
    else:
        tick_pos = xsorig[::stride]
        tick_lab = epoch_labels[::stride]

    return xsorig, epoch_labels, tick_pos, tick_lab, stride

def label_years(fromyearmonth, epochs=None, nepochs=None, stride=1):
    def gen_ym():
        yy, mm = fromyearmonth
        while 1:
            yield (f"{yy}-{mm:02}")
            mm += 1
            if mm == 13:
                mm = 1
                yy += 1
    if epochs is None:
        if nepochs is None:
            raise ValueError("label_years(): provide epochs or nepochs")
        epochs = list(range(nepochs))
    return tuple(zip(*[(i, ym) for (i, ym) in zip(epochs, gen_ym())][::stride]))

def reorderlabels(df):
    labels_slopes = []
    for label in df.columns:
        if label == 'hw': continue
        if not label.startswith("s"): continue
        s, p = slope.linreg(range(len(df[label])), df[label])
        labels_slopes.append((label, s))
    labels_slopes_srt = sorted(labels_slopes, key=lambda s: s[1], reverse=False)
    return [c for c, s in labels_slopes_srt]

def plotdf(df, fname="", usetex=False, fromyearmonth=(2023,4), stride=None, kind='stackbars', reorder=True, interp=None, ifactor=10, sensenames=None, model=None):
    plt.rcParams.update(
        {
            "text.usetex": bool(usetex),
            "font.family": "sans-serif" if not usetex else "serif",
            "font.serif": CM_SERIF_FALLBACK,
            "text.latex.preamble": (
                r"\usepackage[utf8]{inputenc}"
                r"\usepackage[LGR,T2A,T1]{fontenc}"
                r"\usepackage[russian,greek,english]{babel}"
                r"\AtBeginDocument{\selectlanguage{english}}"
            )
            if usetex
            else "",
        }
    )

    fig_width, fig_height = 8, 3  # fixed inches
    fig = plt.figure(figsize=(fig_width, fig_height))

    # Explicitly set plotting area (e.g., left 0.05, right 0.75 leaves 0.25 width for legend)
    ax = fig.add_axes([0.0, 0.27, 0.55, 0.65])  # [left, bottom, width, height]

    if 'hw' in df.columns:
        hw = df['hw'].iloc[0]
    else:
        ivals = df.index.get_level_values("hw")
        uivals = ivals.unique()
        assert len(uivals) == 1
        hw = uivals[0]
        #hw = df.index.unique()[0]
        #assert len(df.index.unique()) == 1
        
    ax.set_title(hw, usetex=False)
    ax.set_frame_on(False)
    ax.set_yticks([])
    xsorig, epoch_labels, xtickposs, xticklabels, stride = _epoch_axis(df, fromyearmonth, stride)
    ax.set_xticks(xtickposs)
    ax.set_xticklabels(xticklabels, rotation=60)
    ax.set_xlabel("epoch")

    labels = reorderlabels(df) if reorder else df.columns
    #labels = df.columns

    if interp is None:
        if kind in ('stackplot', 'plot'):
            interp = True

    xs = xsorig.copy()
    if interp:
        xs = np.linspace(xsorig.min(), xsorig.max(), len(xsorig) * ifactor)

    if kind == 'stackplot':
        yss_labels = []
        labels = labels[::-1]
    if kind == 'stackbars':
        bottoms = pd.Series([0] * len(df) * (ifactor if interp else 1), index=xs)

    for label in labels:
        if label == 'hw': continue
        if not label.startswith("s"): continue

        ys = df[label].to_numpy(copy=False)
        if interp:
            # ty ostatni min osciluji, ale nedaji soucet 1 vsude, musi se pripadne renormalizovat!
            ifunc = scipy.interpolate.Akima1DInterpolator(xsorig, ys)
            #ifunc = scipy.interpolate.PchipInterpolator(df.index, ys)
            #ifunc = scipy.interpolate.CubicSpline(df.index, ys)
            ys = ifunc(xs)

        
        senseno = int(label[1:])
        if sensenames is not None:
            if (hw, senseno) in sensenames.index: neighbors = sensenames.loc[hw, senseno].nn_hw
            elif hw not in sensenames.index.get_level_values('hw'): neighbors = False
            else: neighbors = None
        else:
            try:
                nns = model.nearest(hw, senseno, num_neighbors=10, min_freq=20)
                if math.isnan(nns[0][2]): neighbors = None 
                else: neighbors = [w for (w, nearest_senseno, nearest_sim) in nns]
                text = str(senseno)+ ": "+" ".join(w for (w, nearest_senseno, nearest_sim) in nns[1:6] if '\u03ba' not in w)
            except:
                neighbors = False#label

        if neighbors is False: text = label[1:]
        elif neighbors is None: text = "_"
        else:
            text = str(senseno)+ ": "+" ".join([n for n in neighbors[1:] if '\u03ba' not in n][:6])
        if usetex:
            text = _escape_tex_text(text)

        if kind == 'stackplot':
            yss_labels.append((ys, text))
        elif kind == 'stackbars':
            ax.bar(xs, ys, bottom=bottoms, label=text, width=1)
            bottoms += ys
        elif kind == 'plot':
            ax.plot(xs, ys, label=text)

    if kind == 'stackplot':
        yss = [ys for ys, label in yss_labels]
        ys_labels = [label for ys, label in yss_labels]
        #ax.stackplot(xs, yss, labels=ys_labels, baseline='zero')#baseline='weighted_wiggle')
        ax.stackplot(xs, yss, labels=ys_labels, baseline='weighted_wiggle')

    #ax.set_xlim([f, t])
    #if kind == 'plot':
    #    ax.set_ylim([0, 1])

    # Explicitly define legend box position and size
    legend_box = [0.56, 0.1, 0.43, 0.8]  # [left, bottom, width, height]

    # Create legend inside a defined box
    leg = fig.legend(
        loc='center left',
        bbox_to_anchor=(legend_box[0], legend_box[1] + legend_box[3]/2),
        bbox_transform=fig.transFigure,
        handlelength=0.6, labelspacing=0.3, borderpad=1, fancybox=False,
        framealpha=1, edgecolor='white', reverse=True,
    )

    # Clip legend text to ensure no overflow beyond the legend box
    renderer = fig.canvas.get_renderer()
    max_width = legend_box[2] * fig.bbox.width - 20  # padding in pixels

    for txt in leg.get_texts():
        bbox = txt.get_window_extent(renderer=renderer)
        text = txt.get_text()
        # Clip text visually if necessary
        while bbox.width > max_width and len(text) > 1:
            text = text[:-1]
            txt.set_text(text + '…')
            bbox = txt.get_window_extent(renderer=renderer)

    if fname:
        plt.savefig(fname)
    return fig
    #plt.show()
    #return mpld3.display()

def plotx(df, fname="", usetex=False, fromyearmonth=(2023,4), stride=None, sensenames=None, model=None, hide_empty_senses=False):
    plt.rcParams.setdefault('font.serif')
    plt.rcParams.setdefault('font.family')
    plt.rcParams.setdefault('text.usetex')

    if usetex:
        plt.rcParams.update({
            "text.usetex": True,
            "font.family": "serif",
            "font.serif": CM_SERIF_FALLBACK,
            "text.latex.preamble": (
                r"\usepackage[utf8]{inputenc}"
                r"\usepackage[LGR,T2A,T1]{fontenc}"
                r"\usepackage[russian,greek,english]{babel}"
                r"\AtBeginDocument{\selectlanguage{english}}"
            ),
        })
    else:
        plt.rcParams.update({
            "text.usetex": False,
            "font.family": "serif",
            "font.serif": CM_SERIF_FALLBACK,
            "text.latex.preamble": "",
        })

    # Increase height for words with many senses so label rows do not collide
    # and bottom tick labels (including descenders) are not clipped.
    # Keep scaling moderate to avoid too much whitespace.
    n_senses_est = max(1, len([c for c in df.columns if c.startswith("s")]))
    extra_h = min(1.1, max(0.0, (n_senses_est - 8) * 0.09))
    fig_width, fig_height = 8, 3.4 + extra_h
    fig = plt.figure(figsize=(fig_width, fig_height))

    ivals = df.index.get_level_values("hw")
    uivals = ivals.unique()
    assert len(uivals) == 1
    hw = uivals[0]

    ifactor = 10
    # plotx is denser, keep fewer ticks by default
    if stride is None:
        stride = max(1, int(len(df) / 10))
    xsorig, epoch_labels, xtickposs, xticklabels, stride = _epoch_axis(df, fromyearmonth, stride)

    xs = np.linspace(xsorig.min(), xsorig.max(), len(xsorig) * ifactor)

    cols = [col for col in df.columns if col.startswith("s")]

    goodlabels = []
    if model is None:
        goodlabels = list(cols)
    else:
        for i, label in enumerate(cols):
            senseno = int(label[1:])

            nns = model.nearest(hw, senseno, num_neighbors=10, min_freq=100)
            if not math.isnan(nns[0][2]):
                goodlabels.append(label)

        #if df.sum()[label] > df.filter(regex=("s.*")).sum().sum()/1000.:
        #    goodlabels.append(label)


        #if (hw, senseno) in sensenames.index: neighbors = goodlabels.append(label)
        #elif hw not in sensenames.index.get_level_values('hw'): goodlabels.append(label)#neighbors = False
        #else: neighbors = None
        #
        #try:
        #    nns = model.nearest(hw, senseno, num_neighbors=10, min_freq=20)
        #    if math.isnan(nns[0][2]): neighbors = None 

    if hide_empty_senses:
        goodlabels = [
            label
            for label in goodlabels
            if np.nanmax(np.nan_to_num(df[label].to_numpy(copy=False), nan=0.0)) > 0.0
        ]

    if not goodlabels:
        raise ValueError(f"No senses to plot for {hw} (after filtering).")

    reorder = True
    if reorder:
        labels_slopes = []
        for label in goodlabels:
            s, p = slope.linreg(range(len(df[label])), df[label])
            labels_slopes.append((label, s))
        labels_slopes_srt = sorted(labels_slopes, key=lambda s: s[1], reverse=True)
        goodlabels = [c for c, s in labels_slopes_srt][::-1]

    gs = fig.add_gridspec(len(goodlabels), 8,
                          hspace=0,
                          left=0.02, right=1, top=1, bottom=0.20
                          )
    ax_objs = []

    for i, label in enumerate(goodlabels):
        ys = df[label].reset_index()[label]
        ifunc = scipy.interpolate.Akima1DInterpolator(xsorig, ys)
        #ifunc = scipy.interpolate.PchipInterpolator(df.index, ys)
        #ifunc = scipy.interpolate.CubicSpline(df.index, ys)
        ys = ifunc(xs)
        
        senseno = int(label[1:])
        desc_text = ""
        if sensenames is not None:
            if (hw, senseno) in sensenames.index:
                row = sensenames.loc[hw, senseno]
                neighbors = row.nn_hw if "nn_hw" in row else []
                if "desc" in row and str(row.desc).strip():
                    desc_text = str(row.desc).strip()
            elif hw not in sensenames.index.get_level_values('hw'): neighbors = False
            else: neighbors = None
        else:
            if model is None:
                neighbors = False
            else:
                try:
                    nns = model.nearest(hw, senseno, num_neighbors=10, min_freq=5500)
                    if math.isnan(nns[0][2]): neighbors = None 
                    else: neighbors = [w for (w, nearest_senseno, nearest_sim) in nns]
                    text = str(senseno)+ ": "+" ".join(w for (w, nearest_senseno, nearest_sim) in nns[1:7] if '\u03ba' not in w)
                except:
                    neighbors = False#label

        #if sensenames is not None:
        #    if (hw, senseno) in sensenames.index: neighbors = sensenames.loc[hw, senseno].nn_hw
        #    elif hw not in sensenames.index.get_level_values('hw'): neighbors = False
        #    else: neighbors = None
        #else:
        #    try:
        #        nns = model.nearest(hw, senseno, num_neighbors=10, min_freq=20)
        #        if math.isnan(nns[0][2]): neighbors = None 
        #        else: neighbors = [w for (w, nearest_senseno, nearest_sim) in nns]
        #        text = str(senseno)+ ": "+" ".join(w for (w, nearest_senseno, nearest_sim) in nns[1:6] if '\u03ba' not in w)
        #    except:
        #        neighbors = False#label

        if neighbors is False: text = label[1:]
        elif neighbors is None: text = "_"
        else:
            text = str(senseno)+ ": "+" ".join([n for n in neighbors[1:] if '\u03ba' not in n][:6])

        if desc_text:
            desc_line = desc_text
        else:
            desc_line = ""


        first = i == 0
        last = i == len(goodlabels) - 1
        sharey = sharex = None
        if not first:
            sharey = sharex = ax_objs[-1]
        tab_colors = matplotlib.colormaps["tab10"].colors
        color = tab_colors[i % len(tab_colors)]

        textax = fig.add_subplot(gs[i:i+1, -6:])
        textax.set_axis_off()
        text_main = _truncate_legend(text, max_chars=96)
        text_desc = _truncate_legend(desc_line, max_chars=120) if desc_line else ""

        textax.text(
            0, 0.62 if text_desc else 0.36, text_main,
            ha="left", zorder=1000, va='center', wrap=False, usetex=False, clip_on=True
        )
        if text_desc:
            textax.text(
                0, 0.20, text_desc,
                ha="left", zorder=1000, va='center', wrap=False, usetex=False, fontstyle='italic', clip_on=True
            )
        textax.set_frame_on(False)

        ax = fig.add_subplot(gs[i:i+1, :-6], sharey=sharey, sharex=sharex)
        ax_objs.append(ax)
        ax.plot(xs, ys, color=color, linewidth=1.2)
        ax.fill_between(xs, ys, alpha=0.7, color=color)

        ax.set_xticks(xtickposs, minor=True)
        ax.set_xticklabels(xticklabels, rotation=90, minor=True)
        ax.set_frame_on(False)

        xtickpossMaj, xticklabelsMaj = [], []
        for xx, xpos in enumerate(xtickposs):
            if xticklabels[xx].endswith("01"):
                # Month values are centered on integer positions; year boundaries lie between
                # December and January, i.e. at -0.5 offset from January's center.
                xtickpossMaj.append(xpos - 0.5)
                xticklabelsMaj.append(xticklabels[xx][:4])
        ax.set_xticks(xtickpossMaj, xticklabelsMaj, rotation=90, minor=False)
        ax.grid(visible=True, axis='x', zorder=-1.0, which='major', linewidth=0.6, alpha=0.35)
        ax.grid(visible=True, axis='x', zorder=-1.0, which='minor', linewidth=0.4, alpha=0.15)
        ax.tick_params('y', left=False, which="both", labelleft=False)
        if not last:
            ax.tick_params('x', bottom=False, which="both", labelbottom=False)
            #ax.set_yticks([])
            #ax.set_xticks([])
        else:
            ax.tick_params('x', bottom=False, which="major", labelbottom=False)
        #ax.set_xlim([-0.5, 0.5 + list(epochs)[-1]])
        #ax.set_xlim([-0.5, xsorig.max() + 0.5]) # tohle minimalne vlevo vypada blbe
        ax.set_xlim([0, xsorig.max()])

        for s in "top right left bottom".split():
            ax.spines[s].set_visible(False)
    if fname:
        plt.savefig(fname)
    return fig
    

    

##
#    # creating new axes object
#    ax_objs.append(fig.add_subplot(gs[i:i+1, 0:]))
#
#    # plotting the distribution
#    ax_objs[-1].plot(x_d, np.exp(logprob),color="#f0f0f0",lw=1)
#    ax_objs[-1].fill_between(x_d, np.exp(logprob), alpha=1,color=colors[i])
#
#
#    # setting uniform x and y lims
#    ax_objs[-1].set_xlim(0,1)
#    ax_objs[-1].set_ylim(0,2.5)
#
#    # make background transparent
#    rect = ax_objs[-1].patch
#    rect.set_alpha(0)
#
#    # remove borders, axis ticks, and labels
#    ax_objs[-1].set_yticklabels([])
#
#    if i == len(countries)-1:
#        ax_objs[-1].set_xlabel("Test Score", fontsize=16,fontweight="bold")
#    else:
#        ax_objs[-1].set_xticklabels([])
#
#    spines = ["top","right","left","bottom"]
#    for s in spines:
#        ax_objs[-1].spines[s].set_visible(False)
#
#    adj_country = country.replace(" ","\n")
#    ax_objs[-1].text(-0.02,0,adj_country,fontweight="bold",fontsize=14,ha="right")
#
#
#    i += 1
#
#gs.update(hspace=-0.7)
#
#fig.text(0.07,0.85,"Distribution of Aptitude Test Results from 18 – 24 year-olds",fontsize=20)
#
#plt.tight_layout()
#plt.show()
