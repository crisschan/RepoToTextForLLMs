import os
import gitlab
from tqdm import tqdm
from dotenv import load_dotenv, find_dotenv

# Set your GitLab token here
_=load_dotenv(find_dotenv())

GITLAB_TOKEN = os.getenv('GITLAB_TOKEN')

def get_readme_content(repo, branch='master'):
    """
    Retrieve the content of the README file.
    """
    readme_variants = ['README.md', 'readme.md', 'ReadMe.md']
    
    for readme_name in readme_variants:
        try:
            readme = repo.files.get(file_path=readme_name, ref=branch)
            return readme.decode().decode('utf-8')
        except:
            continue
    
    return "README not found."

def traverse_repo_iteratively(repo):
    """
    Traverse the repository iteratively to avoid recursion limits for large repositories.
    """
    # Get default branch
    default_branch = repo.default_branch
    structure = ""
    dirs_to_visit = [("", repo.repository_tree(ref=default_branch, all=True))]
    dirs_visited = set()

    while dirs_to_visit:
        path, contents = dirs_to_visit.pop()
        dirs_visited.add(path)
        for content in tqdm(contents, desc=f"Processing {path}", leave=False):
            if content['type'] == "tree":
                if content['path'] not in dirs_visited:
                    structure += f"{path}/{content['name']}/\n"
                    dirs_to_visit.append((f"{path}/{content['name']}", repo.repository_tree(path=content['path'], all=True)))
            else:
                structure += f"{path}/{content['name']}\n"
    return structure

def get_file_contents_iteratively(repo,branch='master'):
    # Get default branch
    # default_branch = repo.default_branch
    file_contents = ""
    dirs_to_visit = [("", repo.repository_tree(ref=branch, all=True))]
    dirs_visited = set()
    binary_extensions = [
        # Compiled executables and libraries
        '.exe', '.dll', '.so', '.a', '.lib', '.dylib', '.o', '.obj',
        # Compressed archives
        '.zip', '.tar', '.tar.gz', '.tgz', '.rar', '.7z', '.bz2', '.gz', '.xz', '.z', '.lz', '.lzma', '.lzo', '.rz', '.sz', '.dz',
        # Application-specific files
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp',
        # Media files (less common)
        '.png', '.jpg', '.jpeg', '.gif', '.mp3', '.mp4', '.wav', '.flac', '.ogg', '.avi', '.mkv', '.mov', '.webm', '.wmv', '.m4a', '.aac',
        # Virtual machine and container images
        '.iso', '.vmdk', '.qcow2', '.vdi', '.vhd', '.vhdx', '.ova', '.ovf',
        # Database files
        '.db', '.sqlite', '.mdb', '.accdb', '.frm', '.ibd', '.dbf',
        # Java-related files
        '.jar', '.class', '.war', '.ear', '.jpi',
        # Python bytecode and packages
        '.pyc', '.pyo', '.pyd', '.egg', '.whl',
        # Other potentially important extensions
        '.deb', '.rpm', '.apk', '.msi', '.dmg', '.pkg', '.bin', '.dat', '.data',
        '.dump', '.img', '.toast', '.vcd', '.crx', '.xpi', '.lockb', 'package-lock.json', '.svg' ,
        '.eot', '.otf', '.ttf', '.woff', '.woff2',
        '.ico', '.icns', '.cur',
        '.cab', '.dmp', '.msp', '.msm',
        '.keystore', '.jks', '.truststore', '.cer', '.crt', '.der', '.p7b', '.p7c', '.p12', '.pfx', '.pem', '.csr',
        '.key', '.pub', '.sig', '.pgp', '.gpg',
        '.nupkg', '.snupkg', '.appx', '.msix', '.msp', '.msu',
        '.deb', '.rpm', '.snap', '.flatpak', '.appimage',
        '.ko', '.sys', '.elf',
        '.swf', '.fla', '.swc',
        '.rlib', '.pdb', '.idb', '.pdb', '.dbg',
        '.sdf', '.bak', '.tmp', '.temp', '.log', '.tlog', '.ilk',
        '.bpl', '.dcu', '.dcp', '.dcpil', '.drc',
        '.aps', '.res', '.rsrc', '.rc', '.resx',
        '.prefs', '.properties', '.ini', '.cfg', '.config', '.conf',
        '.DS_Store', '.localized', '.svn', '.git', '.gitignore', '.gitkeep',
    ]

    while dirs_to_visit:
        path, contents = dirs_to_visit.pop()
        dirs_visited.add(path)
        for content in tqdm(contents, desc=f"Downloading {path}", leave=False):
            if content['type'] == "tree":
                if content['path'] not in dirs_visited:
                    dirs_to_visit.append((f"{path}/{content['name']}", repo.repository_tree(path=content['path'], all=True)))
            else:
                # Check if the file extension suggests it's a binary file
                if any(content['name'].endswith(ext) for ext in binary_extensions):
                    file_contents += f"File: {path}/{content['name']}\nContent: Skipped binary file\n\n"
                else:
                    file_contents += f"File: {path}/{content['name']}\n"
                    try:
                        file = repo.files.get(file_path=content['path'], ref=branch)
                        decoded_content = file.decode().decode('utf-8')
                        file_contents += f"Content:\n{decoded_content}\n\n"
                    except UnicodeDecodeError:
                        file_contents += "Content: Skipped due to unsupported encoding\n\n"
    return file_contents

def get_repo_contents(repo_url, branch='master'):
    """
    Main function to get repository contents.
    """
    repo_name = repo_url.split('/')[-1]
    if not GITLAB_TOKEN:
        raise ValueError("Please set 'GITLAB_TOKEN' environment variable or in the script.")
    gl = gitlab.Gitlab('https://gitlab.com', private_token=GITLAB_TOKEN)
    repo = gl.projects.get(repo_url.replace('https://gitlab.com/', ''))

    print(f"Getting README for {repo_name}")
    readme_content = get_readme_content(repo, branch)

    print(f"\nGetting repository structure for {repo_name}")
    repo_structure = f"Repository structure: {repo_name}\n"
    repo_structure += traverse_repo_iteratively(repo)

    print(f"\nGetting file contents for {repo_name}")
    file_contents = get_file_contents_iteratively(repo, branch)

    instructions = "Use the following files and contents for analysis:\n\n"

    return repo_name, instructions, readme_content, repo_structure, file_contents

if __name__ == '__main__':
    repo_url = input("Please enter GitLab repository URL: ")
    branch = input("Please enter branch name (default is master): ") or "master"
    try:
        repo_name, instructions, readme_content, repo_structure, file_contents = get_repo_contents(repo_url, branch)
        output_filename = f'{repo_name}_contents.txt'
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(instructions)
            f.write(f"README:\n{readme_content}\n\n")
            f.write(repo_structure)
            f.write('\n\n')
            f.write(file_contents)
        print(f"Repository contents have been saved to '{output_filename}'.")
    except ValueError as ve:
        print(f"Error: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please check the repository URL and try again.")
