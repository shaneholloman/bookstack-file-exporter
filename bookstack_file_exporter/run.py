import argparse
import os
import logging
from typing import Dict, Union, List

from bookstack_file_exporter.config_helper.config_helper import ConfigNode
from bookstack_file_exporter.exporter import util
from bookstack_file_exporter.exporter.node import Node
from bookstack_file_exporter.archiver import util as archiver_util
from bookstack_file_exporter.archiver.archiver import Archiver


log = logging.getLogger(__name__)

def test(args: argparse.Namespace, token_id_env: str, token_secret_env: str):
    config = ConfigNode(args)
    config.token_id= os.environ.get(token_id_env, "")
    config.token_secret = os.environ.get(token_secret_env, "")

    bookstack_headers = config.headers
    export_formats = config.user_inputs.formats

    ## urls
    shelve_base_url = config.urls['shelves']
    book_base_url = config.urls['books']
    chapter_base_url = config.urls['chapters']
    page_base_url = config.urls['pages']
    
    base_dir_name = archiver_util.generate_root_folder(config.base_dir_name)
    log.info(base_dir_name)

    ## shelves
    all_shelves: List[int] = util.get_all_ids(url=shelve_base_url, headers=bookstack_headers)
    shelve_nodes: Dict[int, Node] = util.get_parent_meta(url=shelve_base_url, headers=bookstack_headers,
                                                         parent_ids=all_shelves)
    
    ## books
    book_nodes: Dict[int, Node] = util.get_child_meta(url=book_base_url, headers=bookstack_headers,
                                                      parent_nodes=shelve_nodes)
    
    ## pages
    page_nodes = util.get_child_meta(url=page_base_url, headers=bookstack_headers, parent_nodes=book_nodes, filter_empty=True)


    ## chapters
    all_chapters: List[int] = util.get_all_ids(url=chapter_base_url, headers=bookstack_headers)
    # check for chapters since they are optional
    if all_chapters:
        chapter_nodes: Dict[int, Node] = util.get_chapter_meta(url=chapter_base_url, headers=bookstack_headers,
                                                            chapters=all_chapters, books=book_nodes)
        # add all pages in a chapter first
        page_chapter_nodes = util.get_child_meta(url=page_base_url, headers=bookstack_headers, parent_nodes=chapter_nodes, filter_empty=True)
        for key, value in page_chapter_nodes.items():
            # if key not in page_nodes: # don't think is needed
            page_nodes[key] = value

    print(chapter_nodes)
    for _, value in chapter_nodes.items():
        print(value.children)

    ## get books with no shelf
    all_books: List[int] = util.get_all_ids(url=book_base_url, headers=bookstack_headers)
    # filter out already seen books
    books_no_shelf = []
    for book_id in all_books:
        if book_id not in book_nodes.keys():
            books_no_shelf.append(book_id)
    

    if books_no_shelf:
        no_shelf_book_nodes = util.get_parent_meta(url=book_base_url, headers=bookstack_headers,
                                                    parent_ids=books_no_shelf, path_prefix=config.unassigned_book_dir)
        no_shelf_page_nodes = util.get_child_meta(url=page_base_url, headers=bookstack_headers,
                                                parent_nodes=no_shelf_book_nodes, filter_empty=True)
        for key, value in no_shelf_page_nodes.items():
            page_nodes[key] = value
    
    
    for key, page in page_nodes.items():
        print(page.file_path)
    
    # for format in config.user_inputs.export_formats:
    #     for key, page in page_nodes.items():
    #         if config.user_inputs.export_meta:
    #             pass

    archive: Archiver = Archiver(base_dir_name, config.user_inputs.outputs)
