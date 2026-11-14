import hashlib
import os
import random
import re
import uuid
from datetime import date, datetime

from flask import Flask, make_response, render_template, session, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, InputRequired
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from PIL import Image, ImageDraw, ImageFont

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


VERIFY_TOKEN = "TUSUR-KANTEEVA-20261108-E79BF825"


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-secret-key")
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "images")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

CHANNEL_ORDERS = [
    ("RGB", (0, 1, 2)),
    ("RBG", (0, 2, 1)),
    ("GRB", (1, 0, 2)),
    ("GBR", (1, 2, 0)),
    ("BRG", (2, 0, 1)),
    ("BGR", (2, 1, 0)),
]


def generate_captcha():
    """Генерирует простую математическую CAPTCHA."""
    operations = [
        ("+", lambda a, b: a + b),
        ("-", lambda a, b: a - b),
        ("*", lambda a, b: a * b),
    ]
    op_symbol, op_func = random.choice(operations)

    if op_symbol == "*":
        a = random.randint(2, 10)
        b = random.randint(2, 10)
    elif op_symbol == "-":
        a = random.randint(10, 50)
        b = random.randint(1, a)
    else:
        a = random.randint(10, 50)
        b = random.randint(10, 50)

    return f"{a} {op_symbol} {b} = ?", op_func(a, b)


class ColorMapForm(FlaskForm):
    image = FileField(
        "Изображение",
        validators=[
            FileRequired(message="Выберите изображение"),
            FileAllowed(["jpg", "jpeg", "png"], "Разрешены только jpg, jpeg и png"),
        ],
    )
    channel_order = SelectField(
        "Порядок каналов R, G, B",
        choices=[(name, name) for name, _ in CHANNEL_ORDERS],
        default="RGB",
        validators=[DataRequired(message="Выберите порядок каналов")],
    )
    captcha_answer = IntegerField(
        "Ответ на задачу",
        validators=[InputRequired(message="Введите ответ на задачу")],
    )
    add_timestamp = BooleanField("Добавить дату и время создания на изображение")
    submit = SubmitField("Изменить цветовые карты")



def apply_channel_order(image_path, order_name):
    """Меняет порядок каналов RGB в соответствии с выбором пользователя."""
    original_img = Image.open(image_path).convert("RGB")
    img_array = np.array(original_img)

    order_indices = (0, 1, 2)
    for name, indices in CHANNEL_ORDERS:
        if name == order_name:
            order_indices = indices
            break

    result_array = img_array[:, :, order_indices]
    result_img = Image.fromarray(result_array.astype("uint8"))
    return original_img, result_img


def add_timestamp_label(image):
    """Добавляет дату и время создания в правый нижний угол изображения."""
    result = image.convert("RGBA")
    overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text = datetime.now().strftime("Создано: %d.%m.%Y %H:%M:%S")
    font_size = max(14, min(result.width, result.height) // 28)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    padding = max(8, font_size // 2)
    x = max(padding, result.width - (right - left) - padding * 2)
    y = max(padding, result.height - (bottom - top) - padding * 2)
    draw.rounded_rectangle(
        (x - padding, y - padding, result.width - padding, result.height - padding),
        radius=max(4, padding // 2),
        fill=(0, 0, 0, 165),
    )
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    return Image.alpha_composite(result, overlay).convert("RGB")



def plot_color_distribution(image, title, filename):
    """Строит график распределения цветов для изображения."""
    img_array = np.array(image.convert("RGB"))
    red = img_array[:, :, 0].ravel()
    green = img_array[:, :, 1].ravel()
    blue = img_array[:, :, 2].ravel()

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(red, bins=256, range=(0, 255), color="red", alpha=0.45, label="R")
    ax.hist(green, bins=256, range=(0, 255), color="green", alpha=0.45, label="G")
    ax.hist(blue, bins=256, range=(0, 255), color="blue", alpha=0.45, label="B")
    ax.set_title(title)
    ax.set_xlabel("Интенсивность пикселя")
    ax.set_ylabel("Количество пикселей")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()

    plot_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    fig.savefig(plot_path, dpi=100)
    plt.close(fig)
    return plot_path



def plot_mean_by_horizontal(image, title, filename):
    """Строит график среднего значения цвета по горизонтали."""
    img_array = np.array(image.convert("RGB"), dtype=np.float32)
    mean_values = np.mean(img_array, axis=1)  # строки
    rows = np.arange(mean_values.shape[0])

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(rows, mean_values[:, 0], color="red", label="R")
    ax.plot(rows, mean_values[:, 1], color="green", label="G")
    ax.plot(rows, mean_values[:, 2], color="blue", label="B")
    ax.set_title(title)
    ax.set_xlabel("Номер строки")
    ax.set_ylabel("Среднее значение цвета")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()

    plot_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    fig.savefig(plot_path, dpi=100)
    plt.close(fig)
    return plot_path



def plot_mean_by_vertical(image, title, filename):
    """Строит график среднего значения цвета по вертикали."""
    img_array = np.array(image.convert("RGB"), dtype=np.float32)
    mean_values = np.mean(img_array, axis=0)  # столбцы
    cols = np.arange(mean_values.shape[0])

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(cols, mean_values[:, 0], color="red", label="R")
    ax.plot(cols, mean_values[:, 1], color="green", label="G")
    ax.plot(cols, mean_values[:, 2], color="blue", label="B")
    ax.set_title(title)
    ax.set_xlabel("Номер столбца")
    ax.set_ylabel("Среднее значение цвета")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()

    plot_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    fig.savefig(plot_path, dpi=100)
    plt.close(fig)
    return plot_path



def clear_old_files():
    """Удаляет старые изображения и графики из папки static/images."""
    folder = app.config["UPLOAD_FOLDER"]
    for filename in os.listdir(folder):
        if filename.startswith(("uploaded_", "result_", "plot_", "swapped_", "resized_")):
            try:
                os.remove(os.path.join(folder, filename))
            except OSError:
                pass


def normalize_html(html):
    """Приводит HTML к каноническому виду для вычисления SHA-256."""
    lines = [line.strip() for line in html.split("\n")]
    lines = [line for line in lines if line]
    lines = [re.sub(r"\s+", " ", line) for line in lines]
    return "\n".join(lines)


@app.get("/health")
def health():
    """Возвращает состояние сервиса для проверки Render."""
    return {"status": "ok"}


@app.get("/verify")
def verify():
    """Возвращает страницу с токеном и контрольным хэшем тела ответа."""
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><title>Verification</title></head>
<body>
<h1>Verification</h1>
<p>Token: {VERIFY_TOKEN}</p>
<p>Date: {date.today().isoformat()}</p>
</body>
</html>"""
    normalized = normalize_html(html)
    response = make_response(html, 200)
    response.headers["X-Verify-Hash"] = hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()
    return response


@app.route("/", methods=["GET", "POST"])
def index():
    form = ColorMapForm()

    if "captcha_answer" not in session:
        question, answer = generate_captcha()
        session["captcha_question"] = question
        session["captcha_answer"] = answer

    captcha_question = session.get("captcha_question", "")
    captcha_error = None

    if form.validate_on_submit():
        user_answer = form.captcha_answer.data
        correct_answer = session.get("captcha_answer")

        if user_answer != correct_answer:
            captcha_error = "Неверный ответ на задачу. Попробуйте ещё раз."
            question, answer = generate_captcha()
            session["captcha_question"] = question
            session["captcha_answer"] = answer
            return render_template(
                "index.html",
                form=form,
                captcha_question=question,
                captcha_error=captcha_error,
            )

        clear_old_files()

        file = form.image.data
        safe_name = secure_filename(file.filename)
        unique_part = uuid.uuid4().hex[:8]
        original_filename = f"uploaded_{unique_part}_{safe_name}"
        original_path = os.path.join(app.config["UPLOAD_FOLDER"], original_filename)
        file.save(original_path)

        channel_order = form.channel_order.data
        original_img, result_img = apply_channel_order(original_path, channel_order)
        timestamp_added = form.add_timestamp.data
        if timestamp_added:
            result_img = add_timestamp_label(result_img)

        result_filename = f"swapped_{unique_part}.png"
        result_path = os.path.join(app.config["UPLOAD_FOLDER"], result_filename)
        result_img.save(result_path)

        plot_distribution = plot_color_distribution(
            original_img,
            "Распределение цветов исходной картинки",
            f"plot_distribution_{unique_part}.png",
        )
        plot_horizontal = plot_mean_by_horizontal(
            original_img,
            "Среднее значение цвета по горизонтали",
            f"plot_horizontal_{unique_part}.png",
        )
        plot_vertical = plot_mean_by_vertical(
            original_img,
            "Среднее значение цвета по вертикали",
            f"plot_vertical_{unique_part}.png",
        )

        question, answer = generate_captcha()
        session["captcha_question"] = question
        session["captcha_answer"] = answer

        return render_template(
            "index.html",
            form=form,
            original_image=url_for("static", filename=f"images/{original_filename}"),
            result_image=url_for("static", filename=f"images/{result_filename}"),
            plot_distribution=url_for("static", filename=f"images/{os.path.basename(plot_distribution)}"),
            plot_horizontal=url_for("static", filename=f"images/{os.path.basename(plot_horizontal)}"),
            plot_vertical=url_for("static", filename=f"images/{os.path.basename(plot_vertical)}"),
            channel_order=channel_order,
            timestamp_added=timestamp_added,
            captcha_question=question,
            captcha_error=captcha_error,
        )

    return render_template(
        "index.html",
        form=form,
        captcha_question=captcha_question,
        captcha_error=captcha_error,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=False, host="0.0.0.0", port=port)
