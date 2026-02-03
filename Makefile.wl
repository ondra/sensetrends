.SECONDARY:
-include config.mk

# Note: this Makefile reflects a local Manatee/SketchEngine setup and is kept
# mainly as a reference. Prefer overriding paths via config.mk.

MANATEE_REGISTRY ?= /mnt/data/ondra/registry/
CORP ?= trends_en_first_20250404
MODEL ?= $(CORP).lempos.e1.d64.w10.a1
SENSETRENDS ?= ./sensetrends
NTHREADS ?= 32
SKIP_FEED ?= doc.feed:https://vetexplainspets.com/feed/
MODELS_DIR ?= /mnt/data/ondra/sensetrends/models/

.PHONY: parts/$(CORP)
parts/$(CORP): $(CORP).lemposes_heads.txt
	mkdir -p parts/$(CORP)
	rm -f parts/$(CORP)/*
	split -d -a3 -l1000 $< parts/$(CORP)/

sensed/$(MODEL)/%: parts/$(CORP)/%
	mkdir -p sensed/$(MODEL)/
	$(SENSETRENDS) --skip '$(SKIP_FEED)' $(MANATEE_REGISTRY)/$(CORP) --nthreads $(NTHREADS) lempos doc.month $(MODELS_DIR)/$(MODEL) <$< >$@ 2>$@.log

sensed/$(MODEL).distrib/%: parts/$(CORP)/%
	mkdir -p sensed/$(MODEL).distrib/
	$(SENSETRENDS) --skip '$(SKIP_FEED)' $(MANATEE_REGISTRY)/$(CORP) --distrib --nthreads $(NTHREADS) lempos doc.month $(MODELS_DIR)/$(MODEL) <$< >$@ 2>$@.log

$(CORP).lemposes_minfreq_100_top100k.txt: $(CORP).lemposes_minfreq_100.txt
	head -n 100000 $< > $@

$(CORP).lemposes_heads.txt: $(CORP).lemposes_minfreq_100_top100k.txt
	cut -f1 $< >$@

$(CORP).lemposes_minfreq_100.txt:
	lswl -l 100000000 -i 100 $(MANATEE_REGISTRY)/$(CORP) lempos > $@
	wc -l $@ 




