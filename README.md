# Covid19SearchEngine

Covid19 search is a search engine dedicated to mine Covid related information. The website mines data from
various authentic websites to answer user queries,performs text summarization and shows false news and rumors
associated with the query. The Repository contains code for the backend REST API built in python and django. The website can be viewed here: http://covid19search.tech/.

When a user enters a query, a few websites that provide authentic covid information are scraped ( We scrape information only from websites that allow scraping). After preprocessing, the information is summarized and provided as an answer to the user’s query. Along with the information retrieved, Google fact check API is used to fetch myths and false news associated with the query and it is filtered out to display only the relevant myths
