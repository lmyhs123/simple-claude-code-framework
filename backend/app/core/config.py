'''
这段代码使用的是 Pydantic 生态中的配置管理模式，这是目前 Python 后端（尤其是 FastAPI 框架）中最流行、最优雅的配置管理方式。
它的核心思想是：定义好数据的类型和默认值，让程序自动去读取环境变量（或 .env 文件），并确保数据类型绝对安全。
'''

from functools import lru_cache
#lru_cache:它是 Python 内置的“缓存”工具。你可以把它理解为一个备忘录，用来记住函数的结果，避免重复计算（后面会详细讲它的妙用）


from pathlib import Path
#Path: 这是处理文件和文件夹路径的现代工具。过去大家喜欢用字符串拼接（比如 dir + "/" + file），不仅容易错，
#在 Windows 和 Mac 上还不兼容。Path 对象让路径操作变得优雅且跨平台。

from pydantic_settings import BaseSettings, SettingsConfigDict
#BaseSettings 与 SettingsConfigDict: 这是 pydantic_settings 库提供的基石。
#任何继承了 BaseSettings 的类，都会自带“自动读取环境变量”的超能力.

class Settings(BaseSettings):
    """类继承 (class Settings(BaseSettings):): 这里我们创建了一个叫 Settings 的蓝图，并让它继承 BaseSettings。
    这意味着它不再是一个普通的类，它在被创建（实例化）的时候，会自动去你的电脑或服务器的环境变量里寻找对应的值。"""

    app_name: str = "Simple Claude Code Framework"
    database_url: str = "sqlite:///./data/app.db"
    upload_dir: str = "./uploads"
    workspace_root: str = ".."
    model_provider: str = "mock"
    model_api_key: str = ""
    model_base_url: str = ""
    model_name: str = ""
    max_agent_steps: int = 5
    max_tool_file_size: int = 1_000_000
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def workspace_path(self) -> Path:
        return Path(self.workspace_root).resolve()
#@property 装饰器: 它的作用是把一个“函数/方法”伪装成一个“属性”。
#为什么要这么做？: self.upload_dir 只是一个普通的字符串（"./uploads"）。但是通过这个方法，我们将它转换成了 Path 对象。
#因为加了 @property，你在其他地方使用时不需要加括号（直接写 settings.upload_path 即可，不用写 settings.upload_path()），
# 用起来就像访问普通变量一样自然。

@lru_cache
def get_settings() -> Settings:
    return Settings()
#读取配置是很慢的: 每次执行 Settings() 时，程序都要去读取 .env 文件、检查系统环境变量、并验证数据类型。
#如果每次需要配置时都执行一遍，会严重拖慢程序速度。
#@lru_cache 的魔法: 当你在 get_settings() 上面贴了这个装饰器后，只有第一次调用这个函数时，
#它会老老实实去读取文件并创建 Settings 对象。从第二次开始，它会直接从内存里把第一次的结果扔给你。
#全局实例: 最后一行 settings = get_settings() 生成了一个全局生效的配置对象。
# 你的其他代码文件只需要导入这个 settings，就能随时随地安全地读取配置了。

settings = get_settings()
