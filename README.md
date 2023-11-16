# Neo-Gung
The all-new backend worker for the [GungGungYouYou](https://gung.joseon.space) webservice.

## 1. Introduction
This is the repository for the total remake of the backend worker of the [GungGungYouYou](https://gung.joseon.space) webservice.
The original backend worker was written just in 2 days without considering the scalability and maintainability with huge issues like:
1. Hardcoded crawling logic, parameters, secrets, and more on over 20 files.
2. No proper logging system.
3. Full of boilerplate code; lack of encapsulation.

After half an year of the original release, the service has grown up to a level that the original backend worker cannot handle.
So I decided to remake the backend worker from scratch, but this time with proper design and architecture driven from the principles of OOP and Clean Architecture.

## 2. Structure

**[log_manager.py](log_manager.py)**: The logging manager that handles all the logging stuffs.
- ColoredFormatter: The formatter that adds colors to the log messages.
- LogManager: The logging manager that handles all the logging stuffs.

**[crawl.py](crawl.py)**: The crawling module that handles all the crawling data from the web.
- BaseCrawler: Includes common crawling logic from initializing the driver to commonly used crawling methods such as `element_from_xpath` and `click_by_xpath`.
- SiteACrawler: The crawler for the site A. (planned)
- SiteBCrawler: The crawler for the site B. (planned)
- Article: The article class that contains the data of the article. This will improve maintainability and readability of the code then just using the dictionary and prone to errors caused by typos.


