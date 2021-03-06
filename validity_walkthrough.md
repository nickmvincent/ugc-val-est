This is a list of steps I've taken after finishing the analysis to check for any potential validity errors.

# Sampling
    Code review
        Reviewed the sampling code in multiple rounds, and after substantial refactoring
    compare descriptive stats of each sample to actual descriptive stats
        Did this at multiple stages (first submission, camera ready)

# Computing features
    Code Review
    checked descriptive stats of all features used in PSM
        Smell test - anything weird like an all zero column, etc
        Do mean values make sense (e.g. percents less than 100, binaries less than 1)

    Manually look over some random samples and verify everything is as expected

    Potentially problematic:
        dummy variables and singular matrices
        readability score
            checked some examples of this manually
        sentiment analysis

    Easier to check:
        Purely mathematical (length of text, percent punctuation, etc)

# PSM
    Check the PSM logistic regression coefficients
    Check the strata
    Check the standardized bias change after performing PSM
    Code review (compared my code to example code from the library)

# Identifying WikiLinks, OtherLinks, GoodWikiLinks, etc
    Compared descriptive stats to descriptive stats of the full dataset on BigQuery
    Run tests to make sure revisions and pageviews are correct
    This is very important because the revision ids are sent to ores to get the article score
    And the article score is how we do analysis in RQ 1.5

    We did run these tests many times
    And did a sanity check to make sure the code that hits the revisions API really only runs for a 2 week period
    (same with pageviews)

    Therefore, I'm 99% sure revisions code is correct.

    Then, I reran all the article quality rating (re-hit the ORES API)
    and reset the "has_c_wiki_link" variables to make sure none had been erroneously marked from before
    After doing this results were THE SAME
    So I have high certainty that there were no errors in this process


Before and after EDITS are checked
Before and after PAGEVIEWS are checked

Editors Gained and Retention scores come from the user info APIs
This is revision specific
    for each revision we need to check that we figured out when the editor
        #1 signed up for WP
        #2 made their MOST RECENT edit

We know revisions are associated correctly
We tested that the code to get WP signup timestamp and most recent edit timestamp work
We reviewed the code that calculated
    #1 was the user signup within the week of analysis?
    #2 was the most recent timestamp 1 month after and 6 months after?
So editors gained and editors retained analysis is correct





