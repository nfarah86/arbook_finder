def write_books(list_book_information, save_directory):
    """reads python text"""
    print(len(list_book_information))
    for book_information in range(len(list_book_information)):
        _write_to_tsv(
            list_book_information[book_information], save_directory)


def _write_to_tsv(book_information, save_directory):
    """ writes to tsv file"""
    with open(save_directory, 'a') as save_book_file:
        format_file = "{!s}\t{!s}\t{!s}\t{!s}\t{!s}\t{!s}\n".format(
            book_information['book_title'],
            book_information['book_author'],
            book_information['book_image_link'],
            book_information['book_rating'],
            book_information['book_word_count'],
            book_information['interest_level']
        )
        save_book_file.write(format_file)
