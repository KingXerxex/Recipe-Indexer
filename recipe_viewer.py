import tkinter as tk
from tkinter import ttk, messagebox
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys
import os
from collections import defaultdict
from fractions import Fraction
import re

# ======================================================================
# PYINSTALLER HELPER
# ======================================================================
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- GLOBAL DATA AND CONFIG ---
all_recipes_data = []
MAX_INGREDIENTS = 20
TOTAL_COLUMNS = 1 + 1 + MAX_INGREDIENTS + 2 # Title + Author + Ingredients + Instructions + date
MEASUREMENT_OPTIONS = [
    " ", "Cup(s)", "Tsp(s)", "Tbsp(s)", "Oz", "Lb(s)", "g", "Kg",
    "mL", "L", "Each", "Pinch", "Dash"
]

# --- GOOGLE SHEETS CONFIGURATION ---
try:
    credentials_file = resource_path('credentials.json')
    SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    CREDS = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, SCOPE)
    CLIENT = gspread.authorize(CREDS)
    SHEET = CLIENT.open("Recipe Index").sheet1
except Exception as e:
    messagebox.showerror("Google Sheets Error", f"Could not connect to Google Sheets.\nPlease check 'credentials.json' and your internet connection.\n\nError: {e}")
    sys.exit()

# ======================================================================
# RECIPE LOGGER WINDOW
# ======================================================================
def open_recipe_logger_window():
    logger_window = tk.Toplevel(window)
    logger_window.title("Recipe Logger")
    logger_window.geometry("525x550") # Set a default size

    # --- Create a main frame and a canvas for scrolling ---
    main_frame = tk.Frame(logger_window)
    main_frame.pack(fill=tk.BOTH, expand=1)

    my_canvas = tk.Canvas(main_frame)
    my_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    # --- Add a scrollbar to the canvas ---
    my_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=my_canvas.yview)
    my_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # --- Configure the canvas ---
    my_canvas.configure(yscrollcommand=my_scrollbar.set)
    my_canvas.bind('<Configure>', lambda e: my_canvas.configure(scrollregion = my_canvas.bbox("all")))

    # --- Create ANOTHER frame INSIDE the canvas ---
    second_frame = tk.Frame(my_canvas)

    # --- Add that new frame to a window in the canvas ---
    my_canvas.create_window((0,0), window=second_frame, anchor="nw")

    def on_mouse_wheel(event):
        my_canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    my_canvas.bind_all("<MouseWheel>", on_mouse_wheel)

    def submit_recipe():
        recipe_title = title_entry.get()
        author_name = author_entry.get()
        if not recipe_title or not author_name:
            messagebox.showerror("Error", "Please fill in both the Title and Author fields.", parent=logger_window)
            return

        ingredients = []
        for i in range(MAX_INGREDIENTS):
            quantity = ingredient_entries[i]['quantity'].get()
            unit = ingredient_entries[i]['unit'].get()
            name = ingredient_entries[i]['name'].get()
            if name:
                ingredients.append(f"{quantity} {unit} {name}".strip())
        
        instructions = instructions_text.get("1.0", tk.END).strip()

        # Create the fixed-width list of data
        row_to_write = [''] * TOTAL_COLUMNS
        
        row_to_write[0] = recipe_title
        row_to_write[1] = author_name
        for i, ingredient in enumerate(ingredients):
            if i < MAX_INGREDIENTS:
                row_to_write[i + 2] = ingredient
        row_to_write[TOTAL_COLUMNS - 2] = instructions
        row_to_write[TOTAL_COLUMNS - 1] = ''

        try:
            # Step 1: Insert the new recipe at the top (row 2)
            SHEET.insert_row(row_to_write, 2, value_input_option='RAW')
            
            messagebox.showinfo("Success", "Recipe submitted successfully!", parent=logger_window)
            
            logger_window.destroy()
            
            refresh_recipe_list()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}", parent=logger_window)

    def clear_fields():
        """Clears all input fields in the logger window."""
        title_entry.delete(0, tk.END)
        author_entry.delete(0, tk.END)
        for i in range(MAX_INGREDIENTS):
            ingredient_entries[i]['quantity'].delete(0, tk.END)
            ingredient_entries[i]['unit'].set('')
            ingredient_entries[i]['name'].delete(0, tk.END)
        instructions_text.delete("1.0", tk.END)

    # --- UI for the Logger Window (now placed in 'second_frame') ---
    title_frame = tk.Frame(second_frame, padx=10, pady=5)
    title_frame.pack(fill='x')
    tk.Label(title_frame, text="Recipe Title:").pack(side='left')
    title_entry = tk.Entry(title_frame)
    title_entry.pack(side='left', expand=True, fill='x')
    # Author Field
    author_frame = tk.Frame(second_frame, padx=10, pady=2)
    author_frame.pack(fill='x')
    tk.Label(author_frame, text="Submitter:", width=15, anchor='w').pack(side='left')
    author_entry = tk.Entry(author_frame)
    author_entry.pack(side='left', expand=True, fill='x')

    ingredients_frame = tk.Frame(second_frame, padx=10, pady=5)
    ingredients_frame.pack()
    ingredient_entries = []
    tk.Label(ingredients_frame, text="Qty").grid(row=0, column=0)
    tk.Label(ingredients_frame, text="Unit").grid(row=0, column=1)
    tk.Label(ingredients_frame, text="Ingredient Name").grid(row=0, column=2)

    for i in range(MAX_INGREDIENTS):
        qty_entry = tk.Entry(ingredients_frame, width=8)
        qty_entry.grid(row=i + 1, column=0, padx=2, pady=2)
        unit_combo = ttk.Combobox(ingredients_frame, width=10, values=MEASUREMENT_OPTIONS)
        unit_combo.grid(row=i + 1, column=1, padx=2, pady=2)
        name_entry = tk.Entry(ingredients_frame, width=30)
        name_entry.grid(row=i + 1, column=2, padx=2, pady=2)
        ingredient_entries.append({'quantity': qty_entry, 'unit': unit_combo, 'name': name_entry})

    instructions_frame = tk.Frame(second_frame, padx=10, pady=5)
    instructions_frame.pack(fill='x')
    tk.Label(instructions_frame, text="Instructions:").pack()
    instructions_text = tk.Text(instructions_frame, width=60, height=10, wrap='word')
    instructions_text.pack(expand=True, fill='both')

    button_frame = tk.Frame(second_frame, pady=10)
    button_frame.pack()
    tk.Button(button_frame, text="Submit Recipe", command=submit_recipe).pack(side='left', padx=5)
    tk.Button(button_frame, text="Clear Fields", command=clear_fields).pack(side='left', padx=5)
# ======================================================================
# GROCERY GENERATOR WINDOW
# ======================================================================
def open_grocery_generator_window():
    """
    Opens a new Toplevel window containing the grocery list generator UI and logic.
    """
    generator_window = tk.Toplevel(window)
    generator_window.title("Grocery List Generator")
    generator_window.geometry("1400x500")

    # This list of counters is now local to this window
    recipe_counters = []

    # --- Helper functions for the generator ---
    def format_fraction(frac):
        """Nicely formats a Fraction object into a string like '1 1/2'."""
        if frac is None: return ""
        if frac.denominator == 1:
            return str(frac.numerator)
        if frac.numerator > frac.denominator:
            whole = frac.numerator // frac.denominator
            rem_num = frac.numerator % frac.denominator
            if rem_num == 0:
                return str(whole)
            return f"{whole} {rem_num}/{frac.denominator}"
        return f"{frac.numerator}/{frac.denominator}"

    def convert_to_fraction(s):
        """Converts a string like '1 1/2' or '3/4' or '2' to a Fraction object."""
        s = s.strip()
        if not s: return Fraction(0)
        try:
            if ' ' in s:
                parts = s.split()
                return int(parts[0]) + Fraction(parts[1])
            return Fraction(s)
        except (ValueError, ZeroDivisionError):
            return Fraction(0)

    def parse_ingredient(ingredient_str):
        """Parses an ingredient string like '2 Cup(s) Flour' into (qty, unit, name)."""
        ingredient_str = ingredient_str.strip()
        # Use a version of the units list without the blank space
        valid_units = [u for u in MEASUREMENT_OPTIONS if u.strip()]
        # Sort units by length, longest first, to match "Tbsp(s)" before "Tsp(s)"
        sorted_units = sorted(valid_units, key=len, reverse=True)
        
        found_unit = ""
        # Create a flexible regex to find the unit, even if it's missing the '(s)'
        for unit in sorted_units:
            # Prepare a regex pattern that ignores the '(s)' for matching purposes
            pattern_base = re.escape(unit.replace('(s)', ''))
            pattern = r'\b' + pattern_base + r'(\(s\))?\b'
            
            match = re.search(pattern, ingredient_str, re.IGNORECASE)
            if match:
                found_unit = match.group(0) # The actual unit found, e.g. "Cup" or "Cup(s)"
                break
        
        if found_unit:
            parts = re.split(r'\b' + re.escape(found_unit) + r'\b', ingredient_str, maxsplit=1, flags=re.IGNORECASE)
            quantity_str = parts[0].strip()
            name_str = parts[1].strip()
            return (quantity_str, found_unit, name_str)
        else:
            # If no unit, assume the first word is quantity if it looks like one
            parts = ingredient_str.split(' ', 1)
            if len(parts) > 1 and re.match(r'^[0-9./\s]+$', parts[0]):
                return (parts[0].strip(), "Each", parts[1].strip())
            else:
                return ("1", "Each", ingredient_str)

    def generate_list():
        selected_recipes = []
        for var, title in recipe_counters:
            if var.get() > 0:
                selected_recipes.append({'title': title, 'count': var.get()})
        
        if not selected_recipes:
            messagebox.showwarning("Warning", "Please add at least one recipe.", parent=generator_window)
            return

        grocery_list = defaultdict(lambda: defaultdict(Fraction))
        for item in selected_recipes:
            for recipe in all_recipes_data:
                if recipe and recipe[0] == item['title']:
                    multiplier = item['count']
                    # Use the correct slice to get all possible ingredient columns
                    all_possible_ingredients = recipe[1:1 + MAX_INGREDIENTS]
                    for ing_str in all_possible_ingredients:
                        if ing_str.strip():
                            qty_str, unit, name = parse_ingredient(ing_str)
                            quantity = convert_to_fraction(qty_str) * multiplier
                            # Normalize name to be lowercase and singular for better grouping
                            name = name.lower().strip()
                            grocery_list[name][unit] += quantity
                    break
        
        # --- MODIFIED FORMATTING SECTION ---
        # Create a list of formatted strings to be sorted
        output_lines = []
        for name, amounts in grocery_list.items():
            for unit, total_quantity in amounts.items():
                if total_quantity > 0:
                    # Format the parts of the line
                    qty_str = format_fraction(total_quantity)
                    unit_str = unit if unit != "Each" else ""
                    # Capitalize the ingredient name for display
                    name_str = name.capitalize()
                    
                    # Add to a list of tuples for sorting: (name, qty, unit)
                    output_lines.append((name_str, qty_str, unit_str))
        
        # Sort the list alphabetically by the ingredient name (the first item in the tuple)
        output_lines.sort(key=lambda x: x[0])

        # Build the final display text with clean alignment
        display_text = ""
        for name_str, qty_str, unit_str in output_lines:
            # Use ljust to left-align the quantity in a fixed-width column
            # This creates the clean alignment you wanted
            aligned_qty = qty_str.ljust(8)
            display_text += f"{aligned_qty}{unit_str} {name_str}\n"

        # --- Display the list ---
        grocery_list_text.config(state='normal')
        grocery_list_text.delete('1.0', tk.END)
        grocery_list_text.insert(tk.END, display_text)
        grocery_list_text.config(state='disabled')

    # --- UI for the new generator window (Unchanged) ---
    left_frame = tk.Frame(generator_window, padx=10, pady=10)
    left_frame.pack(side='left', fill='y')
    right_frame = tk.Frame(generator_window, padx=10, pady=10)
    right_frame.pack(side='right', expand=True, fill='both')

    tk.Label(left_frame, text="Select Meals", font=("Helvetica", 12)).pack()
    canvas = tk.Canvas(left_frame)
    scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    generate_button = tk.Button(right_frame, text="Generate Grocery List", command=generate_list)
    generate_button.pack(pady=10)
    grocery_list_text = tk.Text(right_frame, wrap='word', state='disabled', font=("Courier", 11))
    grocery_list_text.pack(expand=True, fill='both')

    def decrease_count(var):
        if var.get() > 0: var.set(var.get() - 1)
    def increase_count(var):
        var.set(var.get() + 1)

    start_row = 1 if all_recipes_data and all_recipes_data[0][0].lower() in ["title", "recipe title"] else 0
    for row in all_recipes_data[start_row:]:
        if row:
            recipe_title = row[0]
            recipe_frame = ttk.Frame(scrollable_frame)
            recipe_frame.pack(fill='x', expand=True, pady=2)
            count_var = tk.IntVar(value=0)
            ttk.Label(recipe_frame, text=recipe_title).pack(side='left', expand=True, fill='x', padx=5)
            ttk.Button(recipe_frame, text="-", width=3, command=lambda v=count_var: decrease_count(v)).pack(side='left')
            ttk.Label(recipe_frame, textvariable=count_var, width=3, anchor='center').pack(side='left')
            ttk.Button(recipe_frame, text="+", width=3, command=lambda v=count_var: increase_count(v)).pack(side='left')
            recipe_counters.append((count_var, recipe_title))
# ======================================================================
# MAIN RECIPE HUB APPLICATION
# ======================================================================

def delete_selected_recipe():
    """Finds the selected recipe by its index, asks for confirmation, and deletes it."""
    # Get the 0-based index of the selected item in the listbox
    selected_indices = recipe_listbox.curselection()
    if not selected_indices:
        messagebox.showwarning("No Selection", "Please select a recipe from the list to delete.")
        return

    selected_index_in_listbox = selected_indices[0]
    recipe_title = recipe_listbox.get(selected_index_in_listbox)

    # Confirmation dialog
    is_sure = messagebox.askyesno(
        "Confirm Delete",
        f"Are you sure you want to permanently delete '{recipe_title}'?\n\nThis action cannot be undone."
    )

    if not is_sure:
        return  # User clicked "No"

    try:
        # Determine if there's a header row in the sheet to calculate the correct offset
        header_offset = 1 if all_recipes_data and all_recipes_data[0][0].lower() in ["title", "recipe title"] else 0
        row_to_delete = selected_index_in_listbox + header_offset + 1
        SHEET.delete_rows(row_to_delete)
        messagebox.showinfo("Success", f"'{recipe_title}' has been deleted.")
        refresh_recipe_list()  # Update the UI

    except Exception as e:
        messagebox.showerror("API Error", f"An error occurred while deleting the recipe: {e}")


def refresh_recipe_list():
    """Sorts the sheet and then fetches all data to populate the listbox."""
    global all_recipes_data
    try:
        # --- NEW: Sort the sheet before refreshing the data ---
        # This sorts the range A2:V by column 1 (the title, A-Z)
        SHEET.sort((1, 'asc'), range='A2:V' + str(SHEET.row_count))

        # Now, fetch the newly sorted data
        all_recipes_data = SHEET.get_all_values()
        recipe_listbox.delete(0, tk.END)
        
        start_row = 1 if all_recipes_data and all_recipes_data[0][0].lower() in ["title", "recipe title"] else 0
        for row in all_recipes_data[start_row:]:
            if row:
                recipe_listbox.insert(tk.END, row[0])
        
        # Clear display panes
        ingredients_text.config(state='normal'); instructions_text.config(state='normal')
        ingredients_text.delete('1.0', tk.END); instructions_text.delete('1.0', tk.END)
        ingredients_text.config(state='disabled'); instructions_text.config(state='disabled')
    except Exception as e:
        messagebox.showerror("Connection Error", f"Could not refresh recipes.\nError: {e}")

def on_recipe_select(event):
    """Displays the selected recipe's ingredients and instructions."""
    selected_indices = recipe_listbox.curselection()
    if not selected_indices: return
    
    selected_title = recipe_listbox.get(selected_indices[0])
    for recipe in all_recipes_data:
        if recipe and recipe[0] == selected_title:
            author_name = recipe[1] 
            # --- MODIFIED SECTION: Filter out empty ingredient cells ---
            all_possible_ingredients = recipe[2:2 + MAX_INGREDIENTS - 1]
            
            # Only include ingredients that are not empty strings
            actual_ingredients = [ing for ing in all_possible_ingredients if ing.strip()]
            
            ingredients_display = "\n".join(f"- {ing}" for ing in actual_ingredients)
            
            # Ensure instructions are read from the correct, fixed position
            instructions = recipe[TOTAL_COLUMNS - 2] if len(recipe) >= TOTAL_COLUMNS - 2 else ""
            
            ingredients_text.config(state='normal'); instructions_text.config(state='normal')
            ingredients_text.delete('1.0', tk.END); instructions_text.delete('1.0', tk.END)
            ingredients_text.insert(tk.END, ingredients_display); instructions_text.insert(tk.END, instructions)
            ingredients_text.config(state='disabled'); instructions_text.config(state='disabled')
            # Update the author label
            author_label.config(text=f"Submitted by: {author_name}")
            break

# --- MAIN WINDOW GUI SETUP ---
window = tk.Tk()
window.title("Recipe Hub")
window.geometry("800x600")

# --- Top bar for controls ---
top_frame = tk.Frame(window, padx=10, pady=5)
top_frame.pack(side='top', fill='x')

# Buttons on the left
tk.Button(top_frame, text="📝 Add New Recipe", command=open_recipe_logger_window).pack(side='left')
tk.Button(top_frame, text="🛒 Create Grocery List", command=open_grocery_generator_window).pack(side='left', padx=5)
tk.Button(top_frame, text="🔄 Refresh List", command=refresh_recipe_list).pack(side='left')

# --- Removed: Delete button on the right ---

# --- Main Layout Frames ---
list_frame = tk.Frame(window, padx=10, pady=10)
list_frame.pack(side='left', fill='y')
display_frame = tk.Frame(window, padx=10, pady=10)
display_frame.pack(side='right', expand=True, fill='both')

# --- Recipe List (Left Side) ---
tk.Label(list_frame, text="Select a Recipe", font=("Helvetica", 14)).pack(pady=5)
recipe_listbox = tk.Listbox(list_frame, width=30, font=("Helvetica", 12))
recipe_listbox.pack(expand=True, fill='y')
recipe_listbox.bind('<<ListboxSelect>>', on_recipe_select)

# --- Recipe Display (Right Side) ---
tk.Label(display_frame, text="Ingredients", font=("Helvetica", 14)).pack()
ingredients_text = tk.Text(display_frame, height=10, font=("Helvetica", 11), wrap='word', state='disabled')
ingredients_text.pack(expand=True, fill='both', pady=5)
tk.Label(display_frame, text="Instructions", font=("Helvetica", 14)).pack()
instructions_text = tk.Text(display_frame, height=15, font=("Helvetica", 11), wrap='word', state='disabled')
instructions_text.pack(expand=True, fill='both', pady=5)

# --- Author Display Label ---
author_label = tk.Label(display_frame, text="", font=("Helvetica", 10, "italic"), anchor='e')
author_label.pack(fill='x', side='bottom', padx=5)

# --- Load initial data and run the app ---
refresh_recipe_list()
window.mainloop()
