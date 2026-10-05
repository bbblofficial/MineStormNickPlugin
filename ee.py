import os

def print_tree(folder_path, file_handle, prefix="", show_content=False):
    entries = sorted(os.listdir(folder_path))
    for i, entry in enumerate(entries):
        path = os.path.join(folder_path, entry)
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        file_handle.write(f"{prefix}{connector}{entry}\n")

        if os.path.isdir(path):
            extension_prefix = "    " if is_last else "│   "
            print_tree(path, file_handle, prefix + extension_prefix, show_content)
        else:
            if show_content:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            content_lines = content.splitlines()
                            # Content appears directly under the file name
                            for line in content_lines:
                                file_handle.write(f"  {line}\n")  # Just 2 spaces
                except Exception as e:
                    file_handle.write(f"  [Error: {e}]\n")

def save_tree_to_file(output_filename="folder_structure.txt"):
    current_folder = os.path.dirname(os.path.abspath(__file__))
    
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"{current_folder}/\n\n")
        print_tree(current_folder, f, show_content=True)
    
    print(f"Output saved to {output_filename}")

if __name__ == "__main__":
    save_tree_to_file()