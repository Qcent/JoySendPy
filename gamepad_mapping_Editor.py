import pickle
import sys


class PyGameButtonMapping:
    class ButtonMap:
        def __init__(self, input_type=None, index=None, value=None):
            self.input_type = input_type
            self.index = self._to_int(index)
            self.value = self._to_int(value)

        def set(self, type=None, index=None, value=None):
            self.input_type = type
            self.index = self._to_int(index)
            self.value = self._to_int(value)

        def clear(self):
            self.input_type = None
            self.index = None
            self.value = None

        def set_type(self, type):
            self.input_type = type

        def set_index(self, index):
            self.index = self._to_int(index)

        def set_value(self, value):
            self.value = self._to_int(value)

        def val_2_text(self):
            if self.input_type == 2:
                return '+' if self.value > 0 else '-'
            else:
                return "True" if self.value > 0 else "False"

        def type_2_name(self):
            if self.input_type == 1:
                return "Button"
            if self.input_type == 2:
                return "Stick"
            if self.input_type == 4:
                return "Hat"

        @staticmethod
        def _to_int(value):
            try:
                return int(value) if value is not None else None
            except ValueError:
                print(f"Warning: Could not convert value {value} to int. Setting to None.")
                return None

    def __init__(self):
        pass

    def display_button_maps(self):
        button_maps = [attr for attr in dir(self) if isinstance(getattr(self, attr), self.ButtonMap)]
        print("Available button mappings:")
        for i, button_map in enumerate(button_maps):
            bm = getattr(self, button_map)
            print(f"{i}: {button_map} -> {bm.type_2_name()} id: {bm.index}, Value: {bm.val_2_text()}")
        return button_maps

    def display_button_map(self, button_name):
        button_map = getattr(self, button_name)
        # print(f"Details for {button_name}:")
        print(f"  Type: {button_map.type_2_name()}")
        print(f"  Index: {button_map.index}")
        print(f"  Value: {button_map.val_2_text()}1")

    def save_button_maps(self, filename):
        button_list = []
        button_maps = [attr for attr in dir(self) if isinstance(getattr(self, attr), self.ButtonMap)]
        for button_map in button_maps:
            button_list.append([button_map,
                                getattr(self, button_map).input_type,
                                getattr(self, button_map).index,
                                getattr(self, button_map).value])
        with open(filename, 'wb') as f:
            pickle.dump(button_list, f)

    def load_button_maps(self, filename):
        with open(filename, 'rb') as f:
            button_list = pickle.load(f)
        for button_data in button_list:
            button_name, type, index, value = button_data
            setattr(self, button_name, self.ButtonMap(type, index, value))

    def edit_button_map(self, button_name):
        button_map = getattr(self, button_name)
        while True:
            print(f"Editing {button_name}:")
            self.display_button_map(button_name)
            print("Options: (D)one, (T)ype, (I)ndex, (V)alue")
            choice = input("Choose an option: ").strip().upper()
            if choice == 'T':
                new_type = None
                while new_type not in (['1', '2', '4']):
                    print("Options: (1)Button, (2)Stick, (4)Hat")
                    new_type = input("Enter new input type: ").strip()
                button_map.set_type(new_type)
            elif choice == 'I':
                new_index = None
                while not new_index.isdigit():
                    new_index = input("Enter new index: ").strip()
                button_map.set_index(new_index)
            elif choice == 'V':
                new_value = 'None'
                if button_map.input_type == 2:
                    while new_value.lower() not in (['0', '1', '+1', '-1', 't', 'f', 'pos', 'neg', '+', '-']):
                        new_value = input("Enter new value (+1, -1): ").strip()
                    new_value = -1 if new_value in (['-', '0', '-1', 'f', 'neg']) else 1
                else:
                    while new_value.lower() not in (['0', '1', 't', 'f', 'true', 'false']):
                        new_value = input("Enter new value (0, 1): ").strip()
                    new_value = 0 if new_value in (['0', 'false', 'f']) else 1
                button_map.set_value(new_value)
            elif choice == 'D':
                break
            else:
                print("Invalid option. Please try again.")


def display_map_data(file_path):
    button_mapping = PyGameButtonMapping()
    try:
        button_mapping.load_button_maps(file_path)
    except Exception as e:
        print(f"Error loading map data: {e}")
        return

    while True:
        button_maps = button_mapping.display_button_maps()
        choice = input("Enter the index of the button to edit, 'S' to save  or 'Q' to quit: ").strip().upper()
        if choice == 'Q':
            print("Quitting.")
            break
        if choice == 'S':
            print("Saving.")
            button_mapping.save_button_maps(file_path)
        if choice.isdigit():
            index = int(choice)
            if 0 <= index < len(button_maps):
                button_mapping.edit_button_map(button_maps[index])
            else:
                print("Invalid index. Please try again.")
        else:
            print("Invalid input. Please enter a valid index, 'S' to save or 'Q' to quit.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <path_to_map_file>")
    else:
        display_map_data(sys.argv[1])
