import math
import uuid
from io import BytesIO
from pathlib import Path
from typing import Literal, TypeAlias, overload

from nonebot.utils import run_sync
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as tImage
from PIL.ImageFont import FreeTypeFont
from typing_extensions import Self

from ..config import ZxpmConfig

ModeType = Literal[
    "1", "CMYK", "F", "HSV", "I", "L", "LAB", "P", "RGB", "RGBA", "RGBX", "YCbCr"
]
"""图片类型"""

ColorAlias: TypeAlias = str | tuple[int, int, int] | tuple[int, int, int, int] | None

CenterType = Literal["center", "height", "width"]
"""
粘贴居中

center: 水平垂直居中

height: 垂直居中

width: 水平居中
"""

DEFAULT_FONT = ImageFont.load_default()


class BuildImage:
    """
    快捷生成图片与操作图片的工具类
    """

    def __init__(
        self,
        width: int = 0,
        height: int = 0,
        color: ColorAlias = (255, 255, 255),
        mode: ModeType = "RGBA",
        font: str | Path | FreeTypeFont = "HYWenHei-85W.ttf",
        font_size: int = 20,
        background: str | BytesIO | Path | bytes | None = None,
    ) -> None:
        self.uid = uuid.uuid1()
        self.width = width
        self.height = height
        self.color = color
        self.font_size = font_size
        self.font = self.load_font(font_size)
        if background:
            if isinstance(background, bytes):
                self.markImg = Image.open(BytesIO(background))
            else:
                self.markImg = Image.open(background)
            if width and height:
                self.markImg = self.markImg.resize((width, height), Image.LANCZOS)
            else:
                self.width = self.markImg.width
                self.height = self.markImg.height
        elif width and height:
            self.markImg = Image.new(mode, (width, height), color)  # type: ignore
        else:
            raise ValueError("长度和宽度不能为空...")
        self.draw = ImageDraw.Draw(self.markImg)

    @property
    def size(self) -> tuple[int, int]:
        return self.markImg.size

    @classmethod
    def open(cls, path: str | Path | bytes) -> Self:
        """打开图片

        参数:
            path: 图片路径

        返回:
            Self: BuildImage
        """
        return cls(background=path)

    @classmethod
    async def build_text_image(
        cls,
        text: str,
        font: str | FreeTypeFont | Path = "HYWenHei-85W.ttf",
        size: int = 10,
        font_color: str | tuple[int, int, int] = (0, 0, 0),
        color: ColorAlias = None,
        padding: int | tuple[int, int, int, int] | None = None,
    ) -> Self:
        """构建文本图片

        参数:
            text: 文本
            font: 字体路径
            size: 字体大小
            font_color: 字体颜色.
            color: 背景颜色
            padding: 外边距

        返回:
            Self: Self
        """
        if not text.strip():
            return cls(1, 1)
        _font = None
        if isinstance(font, FreeTypeFont):
            _font = font
        elif isinstance(font, str | Path):
            _font = cls.load_font(size)
        width, height = cls.get_text_size(text, _font)
        if isinstance(padding, int):
            width += padding * 2
            height += padding * 2
        elif isinstance(padding, tuple):
            width += padding[1] + padding[3]
            height += padding[0] + padding[2]
        markImg = cls(width, height, color, font=_font)
        await markImg.text(
            (0, 0), text, fill=font_color, font=_font, center_type="center"
        )
        return markImg

    @classmethod
    async def auto_paste(
        cls,
        img_list: list[Self | tImage],
        row: int,
        space: int = 10,
        padding: int = 50,
        color: ColorAlias = (255, 255, 255),
        background: str | BytesIO | Path | None = None,
    ) -> Self:
        """自动贴图

        参数:
            img_list: 图片列表
            row: 一行图片的数量
            space: 图片之间的间距.
            padding: 外边距.
            color: 图片背景颜色.
            background: 图片背景图片.

        返回:
            Self: Self
        """
        if not img_list:
            raise ValueError("贴图类别为空...")
        width, height = img_list[0].size
        background_width = width * row + space * (row - 1) + padding * 2
        row_count = math.ceil(len(img_list) / row)
        if row_count == 1:
            background_width = (
                sum(img.width for img in img_list) + space * (row - 1) + padding * 2
            )
        background_height = height * row_count + space * (row_count - 1) + padding * 2
        background_image = cls(
            background_width, background_height, color=color, background=background
        )
        _cur_width, _cur_height = padding, padding
        for img in img_list:
            await background_image.paste(img, (_cur_width, _cur_height))
            _cur_width += space + img.width
            if _cur_width + padding >= background_image.width:
                _cur_height += space + img.height
                _cur_width = padding
        return background_image

    @classmethod
    def load_font(cls, font_size: int = 10) -> FreeTypeFont:
        """加载字体

        参数:
            font: 字体名称
            font_size: 字体大小

        返回:
            FreeTypeFont: 字体
        """
        return ImageFont.truetype(ZxpmConfig.zxpm_font, font_size)

    @overload
    @classmethod
    def get_text_size(
        cls, text: str, font: FreeTypeFont | None = None
    ) -> tuple[int, int]: ...

    @overload
    @classmethod
    def get_text_size(
        cls, text: str, font: str | None = None, font_size: int = 10
    ) -> tuple[int, int]: ...

    @classmethod
    def get_text_size(
        cls,
        text: str,
        font: str | FreeTypeFont | None = "HYWenHei-85W.ttf",
        font_size: int = 10,
    ) -> tuple[int, int]:  # sourcery skip: remove-unnecessary-cast
        """获取该字体下文本需要的长宽

        参数:
            text: 文本内容
            font: 字体名称或FreeTypeFont
            font_size: 字体大小

        返回:
            tuple[int, int]: 长宽
        """
        _font = font
        if font and isinstance(font, str):
            _font = cls.load_font(font_size)
        temp_image = Image.new("RGB", (1, 1), (255, 255, 255))
        draw = ImageDraw.Draw(temp_image)
        text_box = draw.textbbox((0, 0), str(text), font=_font)  # type: ignore
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        return text_width, text_height + 10
        # return _font.getsize(str(text))  # type: ignore

    def getsize(self, msg: str) -> tuple[int, int]:
        # sourcery skip: remove-unnecessary-cast
        """
        获取文字在该图片 font_size 下所需要的空间

        参数:
            msg: 文本

        返回:
            tuple[int, int]: 长宽
        """
        temp_image = Image.new("RGB", (1, 1), (255, 255, 255))
        draw = ImageDraw.Draw(temp_image)
        text_box = draw.textbbox((0, 0), str(msg), font=self.font)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        return text_width, text_height + 10
        # return self.font.getsize(msg)  # type: ignore

    def __center_xy(
        self,
        pos: tuple[int, int],
        width: int,
        height: int,
        center_type: CenterType | None,
    ) -> tuple[int, int]:
        """
        根据居中类型定位xy

        参数:
            pos: 定位
            image: image
            center_type: 居中类型

        返回:
            tuple[int, int]: 定位
        """
        # _width, _height = pos
        if self.width and self.height:
            if center_type == "center":
                width = int((self.width - width) / 2)
                height = int((self.height - height) / 2)
            elif center_type == "width":
                width = int((self.width - width) / 2)
                height = pos[1]
            elif center_type == "height":
                width = pos[0]
                height = int((self.height - height) / 2)
        return width, height

    @run_sync
    def paste(
        self,
        image: Self | tImage,
        pos: tuple[int, int] = (0, 0),
        center_type: CenterType | None = None,
    ) -> Self:
        """贴图

        参数:
            image: BuildImage 或 Image
            pos: 定位.
            center_type: 居中.

        返回:
            BuildImage: Self

        异常:
            ValueError: 居中类型错误
        """
        if center_type and center_type not in ["center", "height", "width"]:
            raise ValueError("center_type must be 'center', 'width' or 'height'")
        _image = image
        if isinstance(image, BuildImage):
            _image = image.markImg
        if _image.width and _image.height and center_type:
            pos = self.__center_xy(pos, _image.width, _image.height, center_type)
        try:
            self.markImg.paste(_image, pos, _image)  # type: ignore
        except ValueError:
            self.markImg.paste(_image, pos)  # type: ignore
        return self

    @run_sync
    def text(
        self,
        pos: tuple[int, int],
        text: str,
        fill: str | tuple[int, int, int] = (0, 0, 0),
        center_type: CenterType | None = None,
        font: FreeTypeFont | str | Path | None = None,
        font_size: int = 10,
    ) -> Self:  # sourcery skip: remove-unnecessary-cast
        """
        在图片上添加文字

        参数:
            pos: 文字位置
            text: 文字内容
            fill: 文字颜色.
            center_type: 居中类型.
            font: 字体.
            font_size: 字体大小.

        返回:
            BuildImage: Self

        异常:
            ValueError: 居中类型错误
        """
        if center_type and center_type not in ["center", "height", "width"]:
            raise ValueError("center_type must be 'center', 'width' or 'height'")
        max_length_text = ""
        sentence = str(text).split("\n")
        for x in sentence:
            max_length_text = x if len(x) > len(max_length_text) else max_length_text
        if font:
            if not isinstance(font, FreeTypeFont):
                font = self.load_font(font_size)
        else:
            font = self.font
        if center_type:
            ttf_w, ttf_h = self.getsize(max_length_text)  # type: ignore
            # ttf_h = ttf_h * len(sentence)
            pos = self.__center_xy(pos, ttf_w, ttf_h, center_type)
        self.draw.text(pos, str(text), fill=fill, font=font)
        return self

    def show(self):
        """
        说明:
            显示图片
        """
        self.markImg.show()

    def pic2bytes(self) -> bytes:
        """获取bytes

        返回:
            bytes: bytes
        """
        buf = BytesIO()
        self.markImg.save(buf, format="PNG")
        return buf.getvalue()

    @run_sync
    def line(
        self,
        xy: tuple[int, int, int, int],
        fill: tuple[int, int, int] | str = "#D8DEE4",
        width: int = 1,
    ) -> Self:
        """
        画线

        参数:
            xy: 坐标
            fill: 填充.
            width: 线宽.

        返回:
            BuildImage: Self
        """
        self.draw.line(xy, fill, width)
        return self

    @run_sync
    def circle_corner(
        self,
        radii: int = 30,
        point_list: list[Literal["lt", "rt", "lb", "rb"]] | None = None,
    ) -> Self:
        """
        矩形四角变圆

        参数:
            radii: 半径.
            point_list: 需要变化的角.

        返回:
            BuildImage: Self
        """
        if point_list is None:
            point_list = ["lt", "rt", "lb", "rb"]
        # 画圆（用于分离4个角）
        img = self.markImg.convert("RGBA")
        alpha = img.split()[-1]
        circle = Image.new("L", (radii * 2, radii * 2), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, radii * 2, radii * 2), fill=255)  # 黑色方形内切白色圆形
        w, h = img.size
        if "lt" in point_list:
            alpha.paste(circle.crop((0, 0, radii, radii)), (0, 0))
        if "rt" in point_list:
            alpha.paste(circle.crop((radii, 0, radii * 2, radii)), (w - radii, 0))
        if "lb" in point_list:
            alpha.paste(circle.crop((0, radii, radii, radii * 2)), (0, h - radii))
        if "rb" in point_list:
            alpha.paste(
                circle.crop((radii, radii, radii * 2, radii * 2)),
                (w - radii, h - radii),
            )
        img.putalpha(alpha)
        self.markImg = img
        self.draw = ImageDraw.Draw(self.markImg)
        return self