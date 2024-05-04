from playwright.sync_api import sync_playwright
import re
from dotenv import load_dotenv
import os
import subprocess

# Load environment variables from .env file
load_dotenv()
# Read the value of the environment variable
user = os.getenv("USER")
password = os.getenv("PASS")
url = os.getenv("URL")
MAIN_DIRECTORY = os.getenv("MAIN_DIRECTORY")
path_save = None
BIMESTER = os.getenv("BIMESTER")


def login(page):
    page.get_by_role("button", name="Entrar").click()
    page.get_by_placeholder("Digite aqui seu registro").fill(str(user))
    page.get_by_placeholder("Digite aqui sua senha").fill(str(password))
    page.get_by_role("button", name="Acessar o Sistema>").click()
    page.wait_for_timeout(2000)

def get_all_subject_matters(page, select_id):
    '''
    get all subject matters available
    '''
    select_element = page.query_selector(f"select#{select_id}")
    if select_element:
        options = select_element.query_selector_all("option")

        # Filter out the ('', 'SELECIONE...') option
        filtered_options = [(option.get_attribute("value"), option.text_content(
        )) for option in options if option.get_attribute("value") != '']

        return filtered_options
    else:
        print(f"Select element with ID '{select_id}' not found.")
        return []

def create_subject_matter_folder_if_not_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Folder '{folder_path}' created.")

def download_file(url, save_name, save_directory):
    try:
        # Ensure the save directory exists, create if not
        os.makedirs(save_directory, exist_ok=True)
        
        # Full path to save the file
        save_path = os.path.join(save_directory, save_name)
        
        # Run the curl command to download the file
        subprocess.run(['curl', '-o', save_path, url], check=True)
        
        print(f"File downloaded successfully and saved at {save_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading file: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        
def is_field_selected(page, selector):
    field_value = page.eval_on_selector(selector, '(element) => element.value')
    return field_value != ""

def select_and_search(page, value):
    page.get_by_label("Bimestre").select_option(BIMESTER)
    # foreach option_values download files
    page.get_by_label("Materiais Digitais").get_by_label(
        "Componente Curricular").select_option(value)

    page.get_by_role("button", name="Pesquisar").click()

    page.wait_for_timeout(4000)

def reload_if_fail(page, subject_value):
    selector = '.codigoTipoEnsino'  # Replace this with your selector
    is_selected = is_field_selected(page, selector)
    if is_selected:
        print("Field has a value selected:", is_selected)
    else:
        print("Field does not have a value selected")
        page.get_by_role("tab", name="Vídeos").click()
        page.get_by_role("tab", name="Materiais Digitais").click()
        select_and_search(page, subject_value)
        is_selected = is_field_selected(page, selector)

def extract_names_and_urls(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        session_cookies = page.context.cookies()
        login(page)
        page.get_by_role("tab", name="Vídeos").click()
        page.get_by_role("tab", name="Materiais Digitais").click()
        page.wait_for_timeout(3000)
        # Set the captured session cookies to maintain login state
        page.context.add_cookies(session_cookies)
                
        page.get_by_label("Bimestre").select_option(BIMESTER)
        page.get_by_label("Materiais Digitais").get_by_text(
            "Componente Curricular").click()
        select_id = "cdComponenteCurricular"
        option_data = get_all_subject_matters(page, select_id)
        for value, name in option_data:
            print(f"Value: {value}, Name: {name}")
            path_save = f"{MAIN_DIRECTORY}/{name}"
            create_subject_matter_folder_if_not_exists(path_save)

            select_and_search(page, value)
            reload_if_fail(page, value)

            names_and_urls = []

            # Find all elements with class "col-12 col-md-10 mb-2 item"
            items = page.query_selector_all('.col-12.col-md-10.mb-2.item')
            # create a list with title and urls, so we can download the files with friendly names
            for item in items:
                title_element = item.query_selector('.titulo-aula')
                if title_element:
                    title = title_element.text_content()

                    download_link = item.query_selector('.btn-download')
                    if download_link:
                        onclick_value = download_link.get_attribute('onclick')
                        url_match = re.search(
                            r"'(https://[^']+'?)", onclick_value)
                        if url_match:
                            url = url_match.group(1)
                            names_and_urls.append({"title": title, "url": url})
            #  iterate thru title and urls to download and name the files               
            for item in names_and_urls:
                print("Title:", item["title"])
                print("URL:", item["url"][:-1])
                print("---")
            # get name
                # Remove special characters from the name to create a valid file name
                safe_file_name = re.sub(r'[^\w\s-]', '', item["title"]).strip()
                safe_file_name = re.sub(r'[-\s]+', '-', safe_file_name)
                print(safe_file_name)
            # download
                downloaded_file = download_file(
                    item["url"][:-1], f"{safe_file_name}.pdf", path_save)
                
        browser.close()

extract_names_and_urls(url)