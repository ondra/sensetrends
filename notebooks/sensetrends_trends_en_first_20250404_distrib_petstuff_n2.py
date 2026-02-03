#!/usr/bin/env python
# NOTE: This is an exported Jupyter notebook used during experimentation.
# coding: utf-8

# In[1]:


import pylab as plt
import pandas as pd
import slope
import adagram
import math


# In[2]:


modelname = 'trends_en_first_20250404.lempos.e1.d64.w10.a1'
freqs_fnamebase = "../sensed/" + modelname + "/"
modelfname = "../models/" + modelname


# In[3]:


model = adagram.Model(modelfname)


# In[4]:


from read_df import read_df


# In[5]:


dfss = [read_df(freqs_fnamebase + "{:03d}".format(n)) for n in range(1,100)]
dfs = sum(dfss, [])
dfl = dfs
print(len(dfs))


# In[6]:


def mxf(kdf):
    odf = kdf.reset_index().set_index("hw")
    return odf.loc[odf.epoch > 19, :]


# In[ ]:





# In[7]:


dfs = [mxf(loc_df) for loc_df in dfl]


# In[8]:


scols = [c for c in dfs[0].columns if c.startswith('s')]


# In[9]:


def rnorm(df):
    ndf = df.loc[:, scols].div(df.loc[:, 'f'], axis=0)
    ndf['epoch'] = df.epoch
    return ndf.fillna(0.)


# In[10]:


def nnorm(df):
    ndf = df.loc[:, scols].div(df.loc[:, 'n'], axis=0)
    ndf['epoch'] = df.epoch
    return ndf.fillna(0.)


# In[11]:


del plotx
import sys
del sys.modules['plotword']


# In[12]:


from plotword import plotx


# In[13]:


hwmap = {df.index[0]: i for i, df in enumerate(dfs)}


# In[14]:


#xdf = dfs[1]
#print(xdf.index.unique())
#ww = dfs[hwmap["cot-n"]]; ww2 = ww.copy(); ww2.epoch = ww2.epoch.map(lambda x: x-20); plotx(ww2, model=model, fname='cot-n.pdf', fromyearmonth=(2023,5), usetex=True)
#ww = dfs[hwmap["whale-n"]]; ww2 = ww.copy(); ww2.epoch = ww2.epoch.map(lambda x: x-20); plotx(ww2, model=model, fname='whale-n.pdf', fromyearmonth=(2023,5), usetex=True)
#ww = dfs[hwmap["rag-n"]]; ww2 = ww.copy(); ww2.epoch = ww2.epoch.map(lambda x: x-20); plotx(ww2, model=model, fname='rag-n.pdf', fromyearmonth=(2023,5), usetex=True)
ww = dfs[hwmap["nifty-j"]]; ww2 = ww.copy(); ww2.epoch = ww2.epoch.map(lambda x: x-20); plotx(ww2, model=model, fromyearmonth=(2023,5), usetex=True)


# In[15]:


def get_neighbors(hws):
    recs = []
    for hw in hws:
        for sn, mm in enumerate(model.nearest_all(hw, num_neighbors=20, min_freq=20)):
            if math.isnan(mm[0][2]): continue
            for nn_hw, nn_sn, nn_sim in mm:
                recs.append(dict(hw=hw, sn=sn, nn_hw=nn_hw, nn_sn=nn_sn, nn_sim=nn_sim))
    neighs = pd.DataFrame.from_records(recs, index=("hw", "sn"))
    return neighs.sort_index(kind='stable')


# In[ ]:


#xxdf = pd.concat([ddd.reset_index().set_index("hw") for ddd in dfs[200:300]])
#ssdf = get_neighbors(xxdf.index.unique()).sort_index(kind='stable')


# In[ ]:


#xxdf.to_csv("test_senses.tsv", quoting=3, sep='\t')
#ssdf.to_csv("test_hws.tsv", quoting=3, sep='\t')


# In[16]:


plotx(dfs[4212].reset_index().set_index(["hw"]), model=model)
#dfs[1]


# In[ ]:


#plotdf(dfs[hwmap["$-x"]], model=model);


# In[ ]:


#sns = get_neighbors("teta-n kráva-n blbec-n velký-j".split())
#sns2 = sns.sort_index(kind='stable')


# In[ ]:


#" ".join(sns2.loc["blbec-n", 0].nn_hw[1:10])


# In[17]:


nn = 11111
nn = 4122
for n in range(nn, nn+1):
    ddf = rnorm(dfs[n])
    #x = plotdf(ddf, fromyearmonth=(2023, 4), kind='plot', reorder=True);
    #plotx(ddf, fromyearmonth=(2023, 4), model=model);

    ddf = nnorm(dfs[n])

    #ndf = df.loc[:, scols].div(df.loc[:, 'n'], axis=0)
    ddf.loc[:, scols] = ddf.loc[:, scols]*sum(dfs[n].n)*len(ddf.index.unique()) / sum(dfs[n].f)
    #ndf['hw'] = df.hw[0]
    #return ndf.fillna(0.)
    #x = plotdf(ddf, fromyearmonth=(2023, 4), kind='plot', reorder=True);


# In[18]:


def pdf(hw, **kwargs):
    n = hwmap[hw]
    ddf = nnorm(dfs[n])
    #ndf = df.loc[:, scols].div(df.loc[:, 'n'], axis=0)
    ddf.loc[:, scols] = ddf.loc[:, scols]*sum(dfs[n].n)*len(ddf.index.unique()) / sum(dfs[n].f)
    plotdf(ddf, **kwargs)


# In[19]:


def brel(vals):
    f = len(vals) / sum(vals) 
    return vals * f
def brelr(vals): return vals * (1/sum(vals))


# In[20]:


xs = range(len(dfs[0]))
def sslopes(rdf, do_rel):
    out = []
    hw = rdf.index[0]
    for i, c in enumerate(scols):
        series = rdf.loc[:, c]
        ss = sum(series)
        if not ss or math.isnan(ss): continue
        if do_rel: series = brel(series)
        out.append((hw, i, *slope.mk_intercept(xs, series), *slope.linreg_intercept(xs, series)))
    return out


# In[21]:


out = []
for n in range(len(dfs)):
    ddf = nnorm(dfs[n])
    ddf.loc[:, scols] = ddf.loc[:, scols]*sum(dfs[n].n) / sum(dfs[n].f)
    hw = ddf.index[0]
    for i, c in enumerate(scols):
        series = ddf.loc[:, c]
        ss = sum(series)
        if not ss or math.isnan(ss): continue
        try:
            out.append((hw, i, *slope.mk_intercept(xs, series), *slope.linreg_intercept(xs, series)))
        except:
            print(n, hw, xs, flush=1)
            continue
        #print("ok", hw, flush=1)


# In[22]:


trdfrr = pd.DataFrame.from_records(out, columns="hw s mki mks mkp lri lrs lrp".split())
trdfrr['rank'] = trdfrr.hw.map(hwmap)


# In[23]:


dt = trdfrr[(trdfrr.hw == trdfrr.hw.str.lower()) & (trdfrr['rank'] < 30000) & (trdfrr.lrp < 1e-8) & (trdfrr.lrs > 0)].sort_values(by="lrs", ascending=False)
print(len(dt))
print(len(dt.groupby("hw")))
with pd.option_context('display.max_rows', None, 'display.max_columns', None): display(
    dt.head(400)
)


# In[ ]:


#pdf("leopardí-j", kind='plot')
#pdf("semišový-j", kind='plot')
#pdf("introspekce-n", kind='plot')
#pdf("úsekový-j", kind='plot')
#pdf("kalkulátor-n", kind='plot')
#pdf("sofistikovanost-n", kind='plot')
#pdf("diskontní-j", kind='plot')
#pdf("antireflexní-j", kind='plot')
#pdf("vrstvení-n", kind='plot')
#pdf("ležérní-j", kind='plot')
#pdf("stírací-j", kind='plot')
#pdf("vrchovina-n", kind='plot')
#pdf("áčkový-j", kind='plot')
#pdf("trolej-n", kind='plot')
#pdf("provod-n", kind='plot')
#pdf("levhart-n", kind='plot')
#pdf("$-x", kind='plot', usetex=False)
#pdf("prodlužovačka-n", kind='plot', usetex=False)
#pdf("flotilový-j", kind='plot', usetex=False)
#pdf("semiš-n", kind='plot', usetex=False)
#pdf("agregace-n", kind='plot', usetex=False)
#pdf("tachograf-n", kind='plot', usetex=False)
#pdf("koksovna-n", kind='plot', usetex=False)
#pdf("mač-n", kind='plot', usetex=False)

#pdf("look-a", kind='plot', usetex=False)
#pdf("via-p", kind='plot', usetex=False)
#pdf("rozcuchaný-j", kind='plot', usetex=False)
#pdf("silonka-n", kind='plot', usetex=False)
#pdf("hlavolam-n", kind='plot', usetex=False)
#pdf("zlatovláska-n", kind='plot', usetex=False)
#pdf("prsten-n", kind='plot', usetex=False)
#pdf("šarže-n", kind='plot', usetex=False)
#pdf("houf-n", kind='plot', usetex=False)
#pdf("zoom_in-n", kind='plot', usetex=False)
#pdf("závit-n", kind='plot', usetex=False)
#pdf("ks-x", kind='plot', usetex=False)
#pdf("profimedia.cz-n", kind='plot', usetex=False)
#pdf("charisma-n", kind='plot', usetex=False)
#pdf("plynulý-j", kind='plot', usetex=False)

#pdf("substance-n", kind='plot', usetex=False)
#pdf("■-x", kind='plot', usetex=False)
#pdf("býčí-j", kind='plot', usetex=False)
#pdf("účastnice-n", kind='plot', usetex=False)
#pdf("rétorika-n", kind='plot', usetex=False)
#pdf("detekce-n", kind='plot', usetex=False)
#pdf("houf-n", kind='plot', usetex=False)

#pdf("přísaha-n", kind='plot', usetex=False)
#pdf("koksovna-n", kind='plot', usetex=False)









# In[33]:


def gds(ndff, maxrnk=30000, maxp=1e-4, topn=200, ms="mk lr"):
    dts = []
    for tt in ms.split():
        dt = trdfr[(ndff.hw == ndff.hw.str.lower()) & (ndff['rank'] < maxrnk) & (ndff[tt+'p'] < maxp) & (ndff[tt+'s'] > 0)].sort_values(by=tt+"s", ascending=False)
        dts.append(dt)
    return dts

def gss(*args, **kwargs):
    dts = gds(*args, **kwargs)
    os = {}
    for dt in dts:
        for i, (w, grp) in enumerate(dt.groupby("hw", sort=False)):
            if i == 100: break
            topsense = list(grp.s)[0]
            os[w, topsense] = 1
        #for w in list(dt.groupby("hw", sort=False).groups.keys())[:200]:
        #    os[w] = 1
    return list(os.keys())

def gss2(*args, **kwargs):
    dts = gds(*args, **kwargs)
    os = {}
    return [list(dt.groupby("hw", sort=False).groups.keys())[:100] for dt in dts]            


def uk(*lists):
    os = set()
    for li in lists:
        os.update(set(li))
    return sorted(os)

hwwsa = uk(
    gss(trdfr), gss(trdfrr), gss(trdfn),
    gss(trdfr, maxp=1e-7), gss(trdfrr, maxp=1e-7), gss(trdfn, maxp=1e-7),
    gss(trdfr, maxp=1e-5), gss(trdfrr, maxp=1e-5), gss(trdfn, maxp=1e-5)
   )
len(hwwsa)


#        ts = set(dt.groupby("hw")[tt+'s'].max().sort_values(ascending=False).head(topn).index)
#    return set().union(*sts)

#with pd.option_context('display.max_rows', None, 'display.max_columns', None): display(
#    dt.head(5)
#)


# In[34]:


with open(f"en2_heads.tsv", 'w') as of:
    print("hw","sn",sep='\t',file=of)
    for ww in hwwsa:
        print(ww[0],ww[1],sep='\t',file=of)


# In[35]:


for i, r in enumerate((gss(trdfr), gss(trdfrr), gss(trdfn),
        gss(trdfr, maxp=1e-7), gss(trdfrr, maxp=1e-7), gss(trdfn, maxp=1e-7),
        gss(trdfr, maxp=1e-5), gss(trdfrr, maxp=1e-5), gss(trdfn, maxp=1e-5))):
    with open(f"en2_{i}.tsv", 'w') as of:
        print("hw","sn",sep='\t',file=of)
        for ww in r:
            print(ww[0],ww[1],sep='\t',file=of)


# In[36]:


for i, r in enumerate((gss2(trdfr), gss2(trdfrr), gss2(trdfn),
        gss2(trdfr, maxp=1e-7), gss2(trdfrr, maxp=1e-7), gss2(trdfn, maxp=1e-7),
        gss2(trdfr, maxp=1e-5), gss2(trdfrr, maxp=1e-5), gss2(trdfn, maxp=1e-5))):
    with open(f"en2_{i}_mk.tsv", 'w') as of:
        for ww in r[0]:
            print(ww[0],ww[1],sep='\t',file=of)
    with open(f"en2_{i}_lr.tsv", 'w') as of:
        for ww in r[1]:
            print(ww[0],ww[1],sep='\t',file=of)


# In[39]:


import random
random.seed(666)
oll = sorted(set(w for w, _ in hwwsa))
random.shuffle(oll)
oll


# In[40]:


oxdf = pd.concat([ddd.reset_index().set_index("hw") for ddd in (dfs[hwmap[w]] for w in oll)])
osdf = get_neighbors(oxdf.index.unique()).sort_index(kind='stable')
oxdf.to_csv("en2_senses.tsv", quoting=3, sep='\t')
osdf.to_csv("en2_hws.tsv", quoting=3, sep='\t')


# In[ ]:


#xd = gss(trdfr)


# In[ ]:


#oxdf = pd.concat([ddd.reset_index().set_index("hw") for ddd in (dfs[hwmap[w]] for w in oll)])
#osdf = get_neighbors(oxdf.index.unique()).sort_index(kind='stable')
#oxdf.to_csv("cs_senses.tsv", quoting=3, sep='\t')
#osdf.to_csv("cs_hws.tsv", quoting=3, sep='\t')


# In[ ]:


rnorm(dfs[3611]).fillna(0)
#dfs[3611]


# In[24]:


slopr = []
for i, dd in enumerate(dfs):
    rdf = rnorm(dd)
    slopr += sslopes(rdf, do_rel=True)
    if i % 1000 == 0: print (i, end=" ", flush=True)


# In[25]:


trdfr = pd.DataFrame.from_records(slopr, columns="hw s mki mks mkp lri lrs lrp".split())
trdfr['rank'] = trdfr.hw.map(hwmap)


# In[26]:


slopn = []
for i, dd in enumerate(dfs):
    rdf = rnorm(dd)
    slopn += sslopes(rdf, do_rel=False)
    if i % 1000 == 0: print (i, end=" ", flush=True)


# In[27]:


trdfn = pd.DataFrame.from_records(slopn, columns="hw s mki mks mkp lri lrs lrp".split())
trdfn['rank'] = trdfn.hw.map(hwmap)


# In[28]:


trdfr[(trdfr.hw == trdfr.hw.str.lower()) & (trdfr.s != 9) & (trdfr['rank'] < 5000)].sort_values('lrs', ascending=False).head(50).groupby("hw").head()


# In[29]:


import re
ls = trdfn[(trdfn.hw == trdfn.hw.str.lower()) & (trdfn.s != 9) & (trdfn['rank'] < 20000) & (trdfn['lrp'] < 1e-5)].sort_values('lrs', ascending=False).head(30).to_latex()

#ls = trdfr[(trdfr.hw == trdfr.hw.str.lower()) & (trdfr.s != 9) & (trdfr['rank'] < 20000)].sort_values('lrs', ascending=False).head(50).groupby("hw").head().to_latex()
print(re.sub(r'^.*?&', '', ls, flags=re.MULTILINE))


# In[30]:


with pd.option_context('display.max_rows', None, 'display.max_columns', None): display(
    trdfn[(trdfn.hw == trdfn.hw.str.lower()) & (trdfn.s != 9) & (trdfn['rank'] < 20000) & (trdfn['lrp'] < 1e-5)].sort_values('lrs', ascending=False).head(30)
)


# In[31]:


with pd.option_context('display.max_rows', None, 'display.max_columns', None): display(
    trdfn[(trdfn.hw == trdfn.hw.str.lower()) & (trdfn.s != 9) & (trdfn['rank'] < 50000)].sort_values('mks', ascending=False).head(150)
)


# In[ ]:


def ps(xx, **kwargs):
    if 'kind' not in kwargs: kwargs['kind'] = 'plot'
    for hw in xx.split():
        plotdf(rnorm(dfs[hwmap[hw]]), **kwargs)
        plotdf(nnorm(dfs[hwmap[hw]]), **kwargs)


# In[ ]:


#trdf[(trdf.hw == trdf.hw.str.lower()) & (trdf.s != 9) & (trdf.index < 100000)].sort_values('mks', ascending=False).head(50)


# In[ ]:





# In[32]:


hwwsa = uk(
    gss(trdfr), gss(trdfrr), gss(trdfn),
    gss(trdfr, maxp=1e-3), gss(trdfrr, maxp=1e-3), gss(trdfn, maxp=1e-3),
    gss(trdfr, maxp=1e-5), gss(trdfrr, maxp=1e-5), gss(trdfn, maxp=1e-5)
   )
len(hwwsa)
import random
random.seed(666)
oll = list(hwwsa)
random.shuffle(oll)
oll


# In[ ]:


print(len(oll))


# In[ ]:


for i, r in enumerate((gss2(trdfr), gss2(trdfrr), gss2(trdfn),
        gss2(trdfr, maxp=1e-3), gss2(trdfrr, maxp=1e-3), gss2(trdfn, maxp=1e-3),
        gss2(trdfr, maxp=1e-5), gss2(trdfrr, maxp=1e-5), gss2(trdfn, maxp=1e-5))):
    with open(f"en_{i}_mk.tsv", 'w') as of:
        for ww in r[0]:
            print(ww, file=of)
    with open(f"en_{i}_lr.tsv", 'w') as of:
        for ww in r[1]:
            print(ww, file=of)


# In[ ]:


oxdf = pd.concat([ddd for ddd in (dfs[hwmap[w]] for w in oll)])


# In[ ]:


osdf = get_neighbors(oxdf.index.unique()).sort_index(kind='stable')


# In[ ]:


nses = ['oval-j', 'token-j', 'hearty-j', 'tangy-j', 'craftsmanship-n', 'redefin-v', 'fine-tuning-n', 'reg-n', 'tremble-v', 'indulgent-j', 'tumbler-n', 'nahi-n', 'agonist-n', 'podcaster-n', 'gainer-n', 'fav-n', 'decider-n', 'proficiency-n', 'savory-j', 'wicked-j', 'genocidal-j', 'redefine-v', 'coronation-n', 'roadshow-n', 'elasticity-n', 'retrieval-n', 'drizzle-n', 'multimodal-j', 'rapporteur-n', 'counteroffensive-n', 'presale-n', 'easing-n', 'intraday-j', 'aerospace-j', 'prioritising-n', 'incubate-v', '9mm-n', 'felon-n', 'helldiver-n', 'hyaluronic-j', 'advancement-n', 'shipbuilding-n', '8m-n', '50-day-j', 'cost-effectiveness-n', '✨-x', 'greenback-n', 'starrer-n', 'sicken-v', 'nominee-n', 'retribution-n', 'aerospace-n', 'five-on-five-n', 'markdown-n', 'instagram-n', 'electronics-n', 'sectoral-j', 'scalable-j', 'gusty-j', 'reference-i', 'capitalization-n', 'digitization-n', 'wicked-n', 'twister-n', 'cobbles-n', 'refine-v', 'health-conscious-j', 'stab-n', 'autonomously-a', 'prioritizes-v', 'decentralization-n', 'snap-j', 'ultra-processed-j', 'endorse-v', 'tic-n', 'efficiency-n', 'mint-n', '200-day-j', 'pip-n', 'till-i', 'inefficiency-n', 'llama-n', '~-x', 'urbanization-n', 'hai-n', 'vitality-n', 'pharmaceuticals-n', 'telemedicine-n', 'scalability-n', 'chime-v', 'carriageway-n', 'infra-a', 'periscope-n', 'seamless-j', '52-week-j', 'altcoin-n', 'patchy-j', 'ke-n', 'sundown-n', 'exchange-traded-j', 'biodegradable-j', 'independent-n', 'oxidative-j', 'octopus-n', 'purge-v', 'streamline-v', 'unmet-j', 'caseload-n', 'decentralized-j', 'industrialization-n', 'hush-n', 's.-j', 'pug-n', 'ide-n', 'northwest-n', 'elaborate-v']


# In[ ]:


osdf2 = get_neighbors(nses)


# In[ ]:


osdf2.to_csv("en_hws2.tsv", quoting=3, sep='\t')


# In[ ]:


oxdf2 = pd.concat([ddd for ddd in (dfs[hwmap[w]] for w in nses)])


# In[ ]:


pd.concat([oxdf, oxdf2]).to_csv("en_senses.tsv", quoting=3, sep='\t')
pd.concat([osdf, osdf2]).to_csv("en_hws.tsv", quoting=3, sep='\t')


# In[ ]:


oxdf.to_csv("en_senses_new.tsv", quoting=3, sep='\t')
osdf.to_csv("en_hws_new.tsv", quoting=3, sep='\t')


# In[ ]:


import plotword


# In[ ]:


plotword.plotx(dfs[hwmap["whale-n"]], model=model, fromyearmonth=(2023,5))
