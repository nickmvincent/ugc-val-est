# A (relatively detailed) note on some design choices

## What is a Wikipedia link?
We looked for a simple pattern to find wikipedia links: "wikipedia.org/wiki"

Then we used the Wikipedia APIs to identify erroneous links as described below.
The details of exactly how to exclude Wikipedia links did not influence results, mainly because the vsat majority of Wikipedia links were posted were valid links!
Overall, the main purpose of documenting these rare edge cases is to help future work where it might matter more (e.g. analysis that focuses on quality over time; analysis that compares many languages; analysis that wants to include broken links)


## What to do with broken links?
Some users post broken links (e.g. they typed out a Wikipedia article name and mispelled it, the article doesn't exist, etc)
We chose the following pattern:
If the Wikimedia revisions API returns a "missing" error message when trying to get information about the article, mark it as NOT a valid Wikipedia link.
The full list of such urls (only 300 Wikipedia links from 48k SO posts and 36k Reddit posts) is in "url_list.csv" in this folder and that csv file is regenerated when running the full analysis batch in "batch.sh".

## What if there are no revisions, but the Wikimedia API didn't throw an error (rare: affects 0.3% of Wikipedia posts)
If we didn't get a "missing" error from the Wikimedia API, but we also couldn't actually get ANY revisions (in the 2 week period around the post, or before), mark that post so we can see how many meet that criteria. 
These links appear to be caused by Wikipedia article links that were posted before the article was written, e.g.
title: Web_SQL_Database, dates:2010-01-12 20:24:44+00:00_2010-01-26 20:24:44+00:00
or
title: Wiring_(development_platform), dates:2010-07-16 15:32:12+00:00_2010-07-30 15:32:12+00:00
Only 50 Reddit posts and 200 SO posts met that criteria, so we just treated these as stub articles but flagged them with error code 2 (assuming someone might have decided to click the link and create the article, hence potential for a revision). Re-running analysis with and without these posts does not change any conclusions.

## What if ORES can't return a predicted score (very rare: affects 0.1% of Wikipedia posts)
If ORES returns an error for any revisions in the 2 week period, mark it as "missing the ORES score" (day_of_avg_score=None). We don't include these in the Study 2 analyses b/c we were not sure exactly what the error meant. A list of all such links is written to "*_has_link_but_no_ores.csv". This means 57 posts were excluded when computing the reported results. We also included a flag to re-run analysis with and without these posts and found these 0.1% of posts did not influence results at all.
There were 45 posts that were missing an ORES score from a revision before the 2 week period. These were treated as Stub articles.

## Known issues related to non-English articles (rare: affects 1-2% of Wikipedia posts)
For non-English Wikipedia links, the code doesn't try to hit the APIs.
We didn't add explicit handling for non-English Wikipedia links becuase posts with non-English Wikipedia posts make up less than 2% of our Reddit posts and less than 1% of SO posts.
* By default non-English posts are treated as "stub" articles and don't contribute to pageviews/edits. 
This has no effect on the analysis of WP links vs non-WP links. However, it's possible this could affect our quality analysis, or our Reddit/SO effects on WP analysis (because each post would be counted as having zero edits before and after). Therefore, we re-ran the analyses with and without these posts included to make sure this wasn't affecting results in any way, and found it wasn't. In our replications, we chose a simpler option to just treat these as non-WP links.
* Links to Wikipedia articles that are not English Wikipedia, but share a title with an English wikipedia article, may be erroneously associated with the ORES score for that Wikipedia article. We also made sure this not affect reported results, and found it did not.
This bug affects only 44 (0.1%) Reddit posts and 99 (0.2%) SO posts.
Example: https://de.wikipedia.org/wiki/File_Transfer_Protocol
This bug is fixed in the current version of the code.


## Important considerations for future work
Much more careful consideration of non-English Wikipedia posts would be very important for follow-up work that focuses on specific communities (especially sub-reddits that do not use English) or any work that wants to examine effects across different language communities. That being said, the current state of this code is not capable of properly analyzing subcommunities with many links to non-English Wikipedia.

Use of Pageview API: we used the mediawiki pageview API, which (1) returns daily page views and (2) does not return results for dates before Oct. 2015. Therefore, links from before Oct. 2015 are not included in the page view analysis. For more detailed analysis of cross-community relationships (e.g. looking at time series), using hourly page views might be valauble!