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

## Internationalization (i18n)

This project supports multiple languages with Django's internationalization framework. The default language is English, and Portuguese (Brazil) is also supported.

### Managing Translations

#### 1. Extract Messages for Translation

When you add new translatable strings to templates or Python code using `{% trans %}` or `gettext()`, you need to extract them into translation files:

```bash
python manage.py makemessages -l pt_BR
```

This command will:
- Scan all Python files and templates for translatable strings
- Update the existing translation file `locale/pt_BR/LC_MESSAGES/django.po`
- Add new strings that need translation
- Mark obsolete strings for removal

#### 2. Edit Translation Files

After running `makemessages`, edit the generated `.po` files in `locale/pt_BR/LC_MESSAGES/django.po` to add your translations:

```po
#: templates/base.html:13
msgid "Coloring Book"
msgstr "Livro de Colorir"

#: templates/base_site.html:15
msgid "You don't have enough credits"
msgstr "Você não possui créditos suficientes"
```

#### 3. Compile Messages

After editing the translation files, compile them into binary format that Django can use:

```bash
python manage.py compilemessages
```

This command converts `.po` files into `.mo` files that Django uses at runtime.

#### 4. Add New Languages

To add support for a new language (e.g., Spanish):

1. Add the language to `LANGUAGES` in `settings.py`:
   ```python
   LANGUAGES = [
       ("en", "English"),
       ("pt-br", "Português (Brasil)"),
       ("es", "Español"),
   ]
   ```

2. Create message files for the new language:
   ```bash
   python manage.py makemessages -l es
   ```

3. Translate the strings in `locale/es/LC_MESSAGES/django.po`

4. Compile the messages:
   ```bash
   python manage.py compilemessages
   ```

### Language Switching

Users can switch languages using the language selector in the header, which appears on both the landing page and authenticated pages. The language preference is stored in the user's session.

### Development Tips

- Always run `makemessages` after adding new `{% trans %}` tags
- Remember to run `compilemessages` before testing translations
- Use `{% load i18n %}` at the top of templates that use translation tags
- For JavaScript translations, use `makemessages -d djangojs`
