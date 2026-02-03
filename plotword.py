import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import math
import scipy.interpolate
import pandas as pd
import numpy as np
import matplotlib
import slope

def label_years(fromyearmonth, epochs=None, nepochs=None, stride=1):
    def gen_ym():
        yy, mm = fromyearmonth
        while 1:
            yield (f"{yy}-{mm:02}")
            mm += 1
            if mm == 13:
                mm = 1
                yy += 1
    if nepochs: epochs = list(range(epochs))
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
    plt.rcParams.setdefault('font.serif')
    plt.rcParams.setdefault('font.family')
    plt.rcParams.setdefault('text.usetex')

    if usetex:
        plt.rcParams.update({
            "text.usetex": False,
            "font.family": "sans-serif",
            "font.serif": ["Computer Modern Roman"],
        })

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
        
    ax.set_title(hw)
    ax.set_frame_on(False)
    ax.set_yticks([])
    if stride == None:
        stride = int(len(df)/25)
    epochs = df.index if 'epoch' not in df.columns else df.epoch
    xtickposs, xticklabels = label_years(fromyearmonth, epochs=epochs, stride=stride)
    ax.set_xticks(xtickposs, xticklabels, rotation=60)
    ax.set_xlabel("epoch")

    labels = reorderlabels(df) if reorder else df.columns
    #labels = df.columns

    if interp is None:
        if kind in ('stackplot', 'plot'):
            interp = True

    xsorig = (df.index if 'epoch' not in df.columns else df.epoch)
    xs = xsorig.copy()
    if interp:
        xs = np.linspace(min(xs), max(xs), len(xs)*ifactor)

    if kind == 'stackplot':
        yss_labels = []
        labels = labels[::-1]
    if kind == 'stackbars':
        bottoms = pd.Series([0] * len(df) * (ifactor if interp else 1), index=xs)

    for label in labels:
        if label == 'hw': continue
        if not label.startswith("s"): continue

        ys = df[label].reset_index()[label]
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
            text = str(senseno)+ ": "+" ".join([n for n in neighbors[1:] if '\u03ba' not in n][:5])

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

def plotx(df, fname="", usetex=False, fromyearmonth=(2023,4), stride=None, sensenames=None, model=None):
    plt.rcParams.setdefault('font.serif')
    plt.rcParams.setdefault('font.family')
    plt.rcParams.setdefault('text.usetex')

    if usetex:
        plt.rcParams.update({
            "text.usetex": True,
            "font.family": "sans-serif",
            "font.serif": ["Computer Modern Roman"],
        })
    else:
        plt.rcParams.update({
            "text.usetex": False,
            "font.family": "sans-serif",
            "font.serif": ["Computer Modern Roman"],
        })

    fig_width, fig_height = 8, 2.8  # fixed inches
    fig = plt.figure(figsize=(fig_width, fig_height))

    ivals = df.index.get_level_values("hw")
    uivals = ivals.unique()
    assert len(uivals) == 1
    hw = uivals[0]

    epochs = df.epoch

    ifactor = 10
    xsorig = epochs
    xs = xsorig.copy()
    xs = np.linspace(min(xs), max(xs), len(xs)*ifactor)
    if stride == None:
        stride = int(len(df)/10)

    cols = [col for col in df.columns if col.startswith("s")]

    goodlabels = []
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

    reorder = True
    if reorder:
        labels_slopes = []
        for label in goodlabels:
            p, s = slope.linreg(range(len(df[label])), df[label])
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
        if sensenames is not None:
            if (hw, senseno) in sensenames.index: neighbors = sensenames.loc[hw, senseno].nn_hw
            elif hw not in sensenames.index.get_level_values('hw'): neighbors = False
            else: neighbors = None
        else:
            try:
                nns = model.nearest(hw, senseno, num_neighbors=10, min_freq=5500)
                if math.isnan(nns[0][2]): neighbors = None 
                else: neighbors = [w for (w, nearest_senseno, nearest_sim) in nns]
                text = str(senseno)+ ": "+" ".join(w for (w, nearest_senseno, nearest_sim) in nns[1:6] if '\u03ba' not in w)
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
            text = str(senseno)+ ": "+" ".join([n for n in neighbors[1:] if '\u03ba' not in n][:10])


        first = i == 0
        last = i == len(goodlabels) - 1
        sharey = sharex = None
        if not first:
            sharey = sharex = ax_objs[-1]
        color = matplotlib.colormaps['tab10'].colors[i]

        textax = fig.add_subplot(gs[i:i+1, -6:])
        textax.set_axis_off()
        textax.text(0, 0.3, text, ha="left", zorder=1000, va='center', wrap=True)
        textax.set_frame_on(False)

        ax = fig.add_subplot(gs[i:i+1, :-6], sharey=sharey, sharex=sharex)
        ax_objs.append(ax)
        ax.plot(xs, ys, color=color)
        ax.fill_between(xs, ys, alpha=0.7, color=color)

        xtickposs, xticklabels = label_years(fromyearmonth, epochs=epochs, stride=stride)
        ax.set_xticks(xtickposs, xticklabels, rotation=90, minor=True)
        ax.set_frame_on(False)

        xtickpossMaj, xticklabelsMaj = [], []
        for xx, xpos in enumerate(xtickposs):
            if xticklabels[xx].endswith("01"):
                xtickpossMaj.append(xpos - .5)
                xticklabelsMaj.append(xticklabels[xx][:4])
        ax.set_xticks(xtickpossMaj, xticklabelsMaj, rotation=90, minor=False)
        ax.grid(visible=True, axis='x', zorder=-1., which='major')
        ax.tick_params('y', left=False, which="both", labelleft=False)
        if not last:
            ax.tick_params('x', bottom=False, which="both", labelbottom=False)
            #ax.set_yticks([])
            #ax.set_xticks([])
        else:
            ax.tick_params('x', bottom=False, which="major", labelbottom=False)
        #ax.set_xlim([-0.5, 0.5 + list(epochs)[-1]])
        ax.set_xlim([0., list(epochs)[-1]])

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
