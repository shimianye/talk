"""密码哈希工具（bcrypt）。"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """使用 bcrypt 将明文密码转换为不可逆哈希。"""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码是否匹配数据库中的 bcrypt 哈希。"""
    return pwd_context.verify(plain, hashed)
