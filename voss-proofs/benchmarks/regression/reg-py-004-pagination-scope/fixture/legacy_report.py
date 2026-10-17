# TODO: this module is a mess, someone should clean it up
from pagination import page_count

def summary(total,per_page):
    pages=page_count(total,per_page)
    return "%d items on %d pages"%(total,pages)
