import requests


class DataProcessor:
    def __init__(self, url, filename):
        self.url = url
        self.filename = filename

    def fetch_data(self):
        """
        Fetch data from a given URL and return it as a string.
        """
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return None

    def process_data(self, data):
        """
        Process the fetched data by converting it to uppercase.
        """
        if data:
            processed_data = data.upper()
            return processed_data
        else:
            return None

    def save_data(self, data):
        """
        Save processed data to a file.
        """
        try:
            with open(self.filename, 'w') as file:
                file.write(data)
            print(f"Data saved to {self.filename}")
        except IOError as e:
            print(f"Error saving data: {e}")

    def load_data(self):
        """
        Load data from a file.
        """
        try:
            with open(self.filename, 'r') as file:
                data = file.read()
            return data
        except FileNotFoundError:
            print(f"File {self.filename} not found.")
            return None
        except IOError as e:
            print(f"Error loading data: {e}")
            return None

    def process_and_save_data(self):
        """
        Fetch, process, and save data.
        """
        data = self.fetch_data()

        if data:
            processed_data = self.process_data(data)
            print("Processed Data:")
            print(processed_data)

            self.save_data(processed_data)

    def load_and_print_data(self):
        """
        Load and print data from the file.
        """
        # Load data from the file
        loaded_data = self.load_data()
        if loaded_data:
            print("Loaded Data:")
            print(loaded_data)
