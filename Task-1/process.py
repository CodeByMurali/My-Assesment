from data_handlers.processor import DataProcessor


def main():
    url = "https://jsonplaceholder.typicode.com/posts/1"
    filename = "processed_data.txt"

    data_processor = DataProcessor(url, filename)
    data_processor.process_and_save_data()
    data_processor.load_and_print_data()

    non_valid_url = "https://jsonplaceholders.typicode.com/posts/"
    data_processor_2 = DataProcessor(non_valid_url, filename)
    data_processor_2.process_and_save_data()


if __name__ == "__main__":
    main()
