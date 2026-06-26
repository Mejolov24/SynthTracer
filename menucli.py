from collections.abc import Callable


class MenuItem:
    def __init__(self, name : str, type : type, value_name : str = None , value_min = None, value_max = None,  target = None, callback : Callable[[int], None] = None):
        self.name = name
        self.value_name = value_name
        self.type = type
        self.callback = callback
        self.target = target
        self.value_min = value_min
        self.value_max = value_max

class Menu:
    def __init__(self,items : list[MenuItem], callback : Callable[[int,int], None] = None, zero_indexed : bool = False, separator : str = ""):
        self.items = items
        self.callback = callback
        self.zero_indexed = zero_indexed
        self.separator = separator
class Exit: pass

menu_stack : list[Menu] = []

def goToMenu(menu : Menu, append = False):
    if append:
        menu_stack.append(menu)
    else:
        menu_stack.clear()
        menu_stack.append(menu)

def goBack():
    menu_stack.pop()

def _ask_value(type : type, text : str, min = None, max = None):
    while True:
        while True:
            try:
                try:answer = input(text)
                except KeyboardInterrupt : return None
                result = type(answer)
                if (min == None and max == None) : return result
                if (type == int):
                    if not (result < min or result > max) : return result
                    else: print("\033[31m", f"[ERR] Invalid input, must be btween {min} and {max}!","\033[0m")
            except ValueError:
                print("\033[31m", f"[ERR] Invalid input, must be a {type.__name__}!","\033[0m")

def render():
    if len(menu_stack) == 0 : return False
    current_menu : Menu = menu_stack[-1]
    current_menu_items : list[MenuItem] = current_menu.items
    current_menu_length : int = len(current_menu_items) - int(current_menu.zero_indexed)
    print(current_menu.separator)
    for index, item in enumerate(current_menu_items):
        print(index + int(not current_menu.zero_indexed), item.name)
    selection_index : int = _ask_value(int, " Select an option : ",0 + int(not current_menu.zero_indexed),current_menu_length)
    if (selection_index is None) :
        if (current_menu_length < 0): return False
        goBack()
        return render()
        
    selection_index -= int(not current_menu.zero_indexed)
    selection : MenuItem = current_menu_items[selection_index]

    def callback(value):
        if (current_menu.callback) : current_menu.callback(selection_index,value)
        if (selection.callback): selection.callback(value)

    match (selection.type):
        case x if x == callable:
            selection.target()
            callback(None)
        
        case x if x == Menu:
            print(current_menu.separator)
            goToMenu(selection.target,True)
            callback(None)
            return render()

        case x if x == Exit:
            if (len(menu_stack) > 0):
                print(current_menu.separator)
                goBack()
                callback(None)
                return render()
            else :
                callback(None)
                return False

        case _:
            selection_value = _ask_value(selection.type, "  " + selection.value_name, selection.value_min, selection.value_max)
            if (selection_value is None) : return render()
            callback(selection_value)
    return True
