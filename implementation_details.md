# A note on some design choices

What to do with broken links?
People often post broken links (e.g. they typed out a Wikipedia article name and mispelled it, the article doesn't exist, etc)
We chose the following pattern:
If the Wikimedia API returns a "missing" error message when trying to get information about the article, mark it as NOT a valid Wikipedia link.
The full list of such urls (only 300 Wikipedia links from 48k SO posts and 36k Reddit posts) is in "url_list.csv" in this folder and that csv file is regenerated when running the full analysis batch in "batch.sh".

If we didn't get a "missing" error from the Wikimedia API, but we also couldn't actually get ANY revisions (in the 2 week period around the post, or before), mark that post so we can see how many meet that criteria. Only ~50 met that criteria.

For non-English Wikipedia links, don't try to hit the APIs.
We didn't add explicit handling for non-English Wikipedia links becuase posts with non-English Wikipedia posts make up less than 2% of our Reddit posts and less than 1% of SO posts.

Known issues related to non-English articles:
* By default non-English posts are treated as "stub" articles and don't contribute to pageviews/edits. 
This has no effect on the analysis of WP links vs non-WP links. However, it's possible this could affect our quality analysis, or our Reddit/SO effects on WP analysis. Therefore, we re-ran the analyses with and without these posts included to make sure this wasn't affecting results in any way - it wasn't.
* Links to Wikipedia articles that are not English Wikipedia, but share a title with an English wikipedia article, may be erroneously associated with the ORES score for that Wikipedia article.
This bug affects only 44 (0.1%) Reddit posts and 99 (0.2%) SO posts.
Example: https://de.wikipedia.org/wiki/File_Transfer_Protocol

Much more careful consideration of non-English Wikipedia posts would be very important for follow-up work that focuses on specific communities (especially sub-reddits that do not use English) or any work that wants to examine effects across different language communities. That being said, the current state of this code is not capable of properly analyzing subcommunities with many links to non-Englosh Wikipedia.

Use of Pageview API: we used the mediawiki pageview API, which (1) returns daily page views and (2) does not return results for dates before Oct. 2015. Therefore, links from before Oct. 2015 are not included in the page view analysis.