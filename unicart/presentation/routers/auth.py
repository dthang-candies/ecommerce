"""AuthController: UC-01 Register, UC-26 Login/Logout, forgotten password."""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from ...business.actor import Actor
from ...business.extended.mailer import password_reset_mail
from ..extended.deps import RateLimited, current_actor, get_services, reset_budget, reset_ip_budget, throttle
from ..extended.schemas import ChangePasswordIn, ForgotPasswordIn, LoginIn, RegisterIn, ResetPasswordIn
from ..security import create_token
from ..serializers import account_json, customer_json
from ..wiring import Services

router = APIRouter(prefix="/api/auth", tags=["auth"])
Svc = Annotated[Services, Depends(get_services)]


def _session_payload(svc: Services, account) -> dict:
    user = account_json(account)
    if account.role.name == "CUSTOMER":
        user |= {"full_name": svc.customers.profile(account.id).full_name()}
    return {"access_token": create_token(account.id, account.role.name), "token_type": "bearer", "user": user}


@router.post("/register", status_code=201)
def register(body: RegisterIn, svc: Svc):
    account = svc.auth.register(body.email, body.password, body.first_name, body.last_name,
                                body.middle_name, body.phone)
    return _session_payload(svc, account)


@router.post("/login")
def login(body: LoginIn, request: Request, svc: Svc):
    key = f"{body.email.strip().lower()}|{request.client.host if request.client else '-'}"
    throttle.check(key)
    try:
        account = svc.auth.authenticate(body.email, body.password)
    except Exception:
        throttle.failed(key)
        raise
    throttle.succeeded(key)
    return _session_payload(svc, account)


@router.post("/logout", status_code=204)
def logout(_: Annotated[Actor, Depends(current_actor)]):
    """Tokens are stateless and short-lived: the client discards its token."""
    return Response(status_code=204)


@router.get("/me")
def me(actor: Annotated[Actor, Depends(current_actor)], svc: Svc):
    account = svc.auth.get_active(actor.account_id)
    out = account_json(account)
    if actor.role == "CUSTOMER":
        out |= {"profile": customer_json(svc.customers.profile(actor.account_id), account)}
    return out


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordIn, actor: Annotated[Actor, Depends(current_actor)], svc: Svc):
    svc.auth.change_password(actor.account_id, body.old_password, body.new_password)
    return Response(status_code=204)


FORGOT_REPLY = {"message": "Nếu email này đã đăng ký, chúng tôi đã gửi hướng dẫn đặt lại mật khẩu. "
                           "Vui lòng kiểm tra hộp thư (cả mục thư rác)."}


@router.post("/forgot-password", status_code=202)
def forgot_password(body: ForgotPasswordIn, request: Request, tasks: BackgroundTasks, svc: Svc):
    """Always answers the same, whether or not the e-mail is registered. The mail is sent after the response."""
    ip = request.client.host if request.client else "-"
    if not reset_ip_budget.allow(ip):
        raise RateLimited("Bạn gửi yêu cầu quá nhiều lần, vui lòng thử lại sau ít phút")
    if reset_budget.allow(body.email.strip().lower()):                 # per mailbox: silently capped, no mail flood
        issued = svc.auth.request_password_reset(body.email)
        if issued:
            email, token = issued
            tasks.add_task(request.app.state.mailer.send, email, *password_reset_mail(token))
    return FORGOT_REPLY


@router.post("/reset-password", status_code=204)
def reset_password(body: ResetPasswordIn, request: Request, svc: Svc):
    ip = request.client.host if request.client else "-"
    if not reset_ip_budget.allow(ip):
        raise RateLimited("Bạn thử quá nhiều lần, vui lòng thử lại sau ít phút")
    account = svc.auth.reset_password(body.token, body.new_password)
    throttle.succeeded(f"{account.email.lower()}|{ip}")                # the owner is no longer locked out of login
    return Response(status_code=204)
