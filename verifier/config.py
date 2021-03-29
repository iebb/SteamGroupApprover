from sendgrid import Mail

from verifier.settings import SENDER_EMAIL


def build_mail(user):
    return Mail(
        from_email=SENDER_EMAIL,
        to_emails=user.email,
        subject=f'{user.personaname}，为 SYSUPause 群组验证该邮箱',
        html_content=(
            f'<strong>Steam 用户 {user.personaname} ({user.profileurl}) 正在尝试使用你的邮箱进行认证: </strong><br/>'
            f'<strong>请点击以下链接完成 SYSUPause 邮箱验证，验证有效期为 30 分钟:</strong><br/>'
            f'<a href="{user.get_verify_link()}">{user.get_verify_link()}</a>'
        )
    )