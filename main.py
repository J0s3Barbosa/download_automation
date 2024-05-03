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
url = 'https://repositorio.educacao.sp.gov.br/Inicio/MidiasCMSP#'
main_directory = f"playwright/download/"
path_save = None


def login(page):
    page.get_by_role("button", name="Entrar").click()
    page.get_by_placeholder("Digite aqui seu registro").fill(str(user))
    page.get_by_placeholder("Digite aqui sua senha").fill(str(password))
    page.get_by_role("button", name="Acessar o Sistema>").click()
    page.wait_for_timeout(2000)


def get_select_options(page, select_id):
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


def create_folder_if_not_exists(folder_path):
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


def extract_names_and_urls(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        session_cookies = page.context.cookies()
        login(page)
        page.wait_for_timeout(5000)

        # Set the captured session cookies to maintain login state
        page.context.add_cookies(session_cookies)
        bimester = "2"
        page.get_by_label("Bimestre").select_option(bimester)
        page.get_by_label("Materiais Digitais").get_by_text(
            "Componente Curricular").click()
        select_id = "cdComponenteCurricular"
        option_data = get_select_options(page, select_id)
        for value, name in option_data:
            print(f"Value: {value}, Name: {name}")
            path_save = f"{main_directory}/{name}"
            create_folder_if_not_exists(path_save)

            page.get_by_label("Bimestre").select_option(bimester)
            # foreach option_values download files
            page.get_by_label("Materiais Digitais").get_by_label(
                "Componente Curricular").select_option(value)

            page.get_by_role("button", name="Pesquisar").click()
            page.wait_for_timeout(3000)
            # Get the HTML content of the page
            html_code = page.content()

            # Set the content of the page to the provided HTML code
            page.set_content(html_code)

            names_and_urls = []

            # Find all elements with class "col-12 col-md-10 mb-2 item"
            items = page.query_selector_all('.col-12.col-md-10.mb-2.item')
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
