#!/usr/bin/env python3
import os
import requests
import pandas as pd
import sys

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if not API_KEY:
    print("Error: set OPENROUTER_API_KEY environment variable", file=sys.stderr)
    sys.exit(1)
model = 'openai/gpt-oss-120b'
BASEURL = 'https://openrouter.ai/api/v1/chat/completions'

concfile = sys.argv[1]
lang = 'English'

concs = pd.read_csv(concfile, sep="\t", index_col="hw sn".split(), quoting=3)

grammar = r"""root ::= lines
number ::= [1-9][0-9]*
line ::= number "\t" number "\n"
lines ::= line lines?"""

def grammar_for_sns(sns):
    grammar = 'root ::= ' + ' '.join(f'sl{n}' for n in sns) 
    grammar += '\n'.join(
            f'sl{n} ::= "{n}" "\t" def "\\n"'
        for n in sns)
    grammar += 'def ::= [^\\n\\t]+'
    return grammar

print("hw", "sn", "description", "collocation", sep='\t', flush=1)
for hw in concs.index.levels[0]:
    conc_rows = concs.loc[hw].groupby('sn').sample(15, random_state=42)

    ctxs = ""
    for row in conc_rows.itertuples():
        ctxs += f"{hw}#{row.Index}:" + row.lctx + '<' + row.kw + '>' + row.rctx + "\n"

    prompt = f"You are a linguistic researcher. You will decide the context, in which the word marked between '<' and '>' is used in the following collection of text snippets. The target lemma and part-of-speech combination common for all the snippets provided by an external tool, which can make mistakes, is '{hw}'. Each snippet starts with the target lemma+PoS and a cluster number. The snippets are: \n"

    senses = conc_rows.index.unique()

    prompt_end = f"\nWhat contexts or word senses are represented by the different clusters? In what the clusters differ from the others, what is specific for them? For each cluster, output the cluster number, TAB character, and the name or description of the context (avoid using any forms of the target lemma; use at most 6 words), TAB character, and an example representative collocation (as it would appears in normal text, at most 3 words). One cluster per line. Use simple, basic language. Provide the answer in {lang}."
    payload = {'model': model, 'temperature': 0, 'structured_outputs': {'grammar': grammar_for_sns(senses) }, 
            'messages': [{'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': prompt + ctxs + prompt_end}]}

    try:
        response = requests.post(BASEURL,
            headers={'Authorization': f'Bearer {API_KEY}'}, json=payload)
        resp = response.json()['choices'][0]['message']['content']
        print(response.json(), file=sys.stderr)
        for line in resp.splitlines():
            line = line.strip()
            print(hw, line, sep='\t', file=sys.stderr)
            print(hw, line.replace('\\t', '\t'), sep='\t', flush=1)
    except Exception as e:
        print("ERR", hw, str(e).replace("\n", "##ENDLINE##"), sep='\t', file=sys.stderr)
        print(response.text, file=sys.stderr)
        #print(hw, 'error', str(e).replace("\n", "##ENDLINE##").replace("\t", "##TAB##"), sep='\t', flush=1)

