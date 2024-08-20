from fasthtml.common import *
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
import os
import base64
import re

app, rt = fast_app()

# Function to extract content from HTML, properly handling images
def process_html_content(html_content, book):
    soup = BeautifulSoup(html_content, 'html.parser')
    for img in soup.find_all('img'):
        if img.get('src'):
            src = img['src']
            item = book.get_item_with_href(src)
            if item:
                img_content = item.get_content()
                img_base64 = base64.b64encode(img_content).decode('utf-8')
                img['src'] = f"data:image/png;base64,{img_base64}"
    return str(soup)

# Function to split content into pages
def split_into_pages(content, max_chars=3000):
    pages = []
    current_page = ""
    for paragraph in re.split(r'(<p>.*?</p>|<img.*?>)', content, flags=re.DOTALL):
        if not paragraph.strip():
            continue
        if len(current_page) + len(paragraph) > max_chars and current_page:
            pages.append(current_page)
            current_page = paragraph
        else:
            current_page += paragraph
    if current_page:
        pages.append(current_page)
    return pages

# Function to extract TOC
def extract_toc(book):
    toc = []
    for item in book.get_items_of_type(ebooklib.ITEM_NAVIGATION):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        for nav_point in soup.find_all('navPoint'):
            toc.append({
                'label': nav_point.find('text').text,
                'href': nav_point.find('content')['src']
            })
    return toc

# Function to process uploaded epub file
def process_epub(file_path):
    book = epub.read_epub(file_path)
    all_content = ""
    toc = extract_toc(book)
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = process_html_content(item.get_content().decode('utf-8'), book)
            all_content += content
    return split_into_pages(all_content), toc

@rt('/')
def get():
    return Titled("Epub Reader",
        H1("Epub Reader"),
        Form(
            Input(type="file", name="epub_file", accept=".epub"),
            Button("Upload"),
            id="upload-form",
            hx_post="/upload",
            hx_target="#content",
            hx_encoding="multipart/form-data"
        ),
        Div(id="content")
    )

@rt('/upload')
async def post(request):
    form = await request.form()
    epub_file = form['epub_file']
    
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(epub_file.file.read())
        temp_path = temp_file.name

    pages, toc = process_epub(temp_path)
    os.unlink(temp_path)

    nav_buttons = Div(
        Button("Previous", id="prev-btn", onclick="prevPage()"),
        Button("Next", id="next-btn", onclick="nextPage()"),
        id="nav-buttons"
    )
    progress_bar = Div(
        Div(id="progress-fill", style="width: 0%;"),
        id="progress-bar"
    )
    page_count = Div(id="page-count")
    page_content = Div(id="page-content")
    
    js = """
    let currentPage = 0;
    const pages = %s;
    
    function displayPage() {
        document.getElementById('page-content').innerHTML = pages[currentPage];
        document.getElementById('page-count').innerText = `Page ${currentPage + 1} of ${pages.length}`;
        const progressPercentage = ((currentPage + 1) / pages.length) * 100;
        document.getElementById('progress-fill').style.width = `${progressPercentage}%%`;
        addParagraphHighlighting();
    }
    
    function nextPage() {
        if (currentPage < pages.length - 1) {
            currentPage++;
            displayPage();
        }
    }
    
    function prevPage() {
        if (currentPage > 0) {
            currentPage--;
            displayPage();
        }
    }
    
    function addParagraphHighlighting() {
        const paragraphs = document.querySelectorAll('#page-content p');
        paragraphs.forEach(p => {
            p.addEventListener('click', function() {
                paragraphs.forEach(p => p.classList.remove('highlighted'));
                this.classList.add('highlighted');
            });
        });
    }
    
    displayPage();
    """ % str(pages)

    css = """
    #progress-bar {
        width: 100%%;
        height: 20px;
        background-color: #f0f0f0;
        margin: 10px 0;
    }
    #progress-fill {
        height: 100%%;
        background-color: #4CAF50;
        transition: width 0.3s ease-in-out;
    }
    .highlighted {
        background-color: yellow;
    }
    #page-content img {
        max-width: 100%%;
        height: auto;
    }
    #page-content {
        max-height: 80vh;
        overflow-y: auto;
        padding: 20px;
        border: 1px solid #ddd;
    }
    """

    return Div(
        nav_buttons,
        progress_bar,
        page_count,
        page_content,
        Style(css),
        Script(js)
    )

serve()
