# Coloring Book Image Converter

This Django project allows you to upload an image and convert it into a black-and-white sketch, like a coloring book page.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create a virtual environment and activate it:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Apply the database migrations:**

    ```bash
    python manage.py migrate
    ```

## Usage

1.  **Start the development server:**

    ```bash
    python manage.py runserver
    ```

2.  **Open your web browser and go to:**

    ```
    http://127.0.0.1:8000/
    ```

3.  **Upload an image and click the "Convert" button.**

4.  **The original and converted images will be displayed on the page.**

5.  **You can download the converted image by clicking the "Download Sketch" link.**
