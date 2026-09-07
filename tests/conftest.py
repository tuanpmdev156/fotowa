import os

import pytest
from playwright.sync_api import sync_playwright

from pages.login_page import LoginPage

@pytest.fixture(scope="session")
def login_url():
     return os.getenv("LOGIN_URL", "https://master.review.fotowa.com/users/sign_in")

@pytest.fixture(scope="session")
def browser_context():
    with sync_playwright() as p:
        USER_DATA_DIR = r"C:\Users\Lenovo\AppData\Local\Google\Chrome\User Data\Profile 15"
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",
            headless=False,
        )
        yield context
        context.close()

@pytest.fixture
def login_page(page,login_url):
    return LoginPage(page,login_url)