.SECONDARY:
export PATH:=/home/ondra/manfin/manatee/api:/home/ondra/manfin/manatee/api/.libs:/home/ondra/manfin/manatee/api/sketch/.libs:/home/ondra/manfin/manatee/src:/home/ondra/manfin/manatee/sketch:/home/ondra/manfin/manatee/fsa3:/home/ondra/manfin/manatee/go:$(PATH)

MANATEE_REGISTRY=/mnt/data/ondra/registry/
CORP=trends_en_first_20250404
MODEL=$(CORP).lempos.e1.d64.w10.a1

.PHONY: parts/$(MODEL)
parts/$(CORP): $(CORP).lemposes_heads.txt
	mkdir -p parts/$(CORP)
	rm -f parts/$(CORP)/*
	split -d -a3 -l1000 $< parts/$(CORP)/

sensed/$(MODEL)/%: parts/$(CORP)/%
	mkdir -p sensed/$(MODEL)/
	./sensetrends --skip 'doc.feed:https://vetexplainspets.com/feed/' $(MANATEE_REGISTRY)/$(CORP) --nthreads 32 lempos doc.month /mnt/data/ondra/sensetrends/models/$(MODEL) <$< >$@ 2>$@.log

sensed/$(MODEL).distrib/%: parts/$(CORP)/%
	mkdir -p sensed/$(MODEL).distrib/
	./sensetrends --skip 'doc.feed:https://vetexplainspets.com/feed/' $(MANATEE_REGISTRY)/$(CORP) --distrib --nthreads 32 lempos doc.month /mnt/data/ondra/sensetrends/models/$(MODEL) <$< >$@ 2>$@.log

$(CORP).lemposes_minfreq_100_top100k.txt: $(CORP).lemposes_minfreq_100.txt
	head -n 100000 $< > $@

$(CORP).lemposes_heads.txt: $(CORP).lemposes_minfreq_100_top100k.txt
	cut -f1 $< >$@

$(CORP).lemposes_minfreq_100.txt:
	lswl -l 100000000 -i 100 $(MANATEE_REGISTRY)/$(CORP) lempos > $@
	wc -l $@





