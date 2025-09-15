# capistack/web/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash
from sqlalchemy import select
from capistack.db.session import SessionLocal
from capistack.db.models import Project, Deployment

web_bp = Blueprint("web", __name__)

@web_bp.get("/")
def dashboard():
    with SessionLocal() as s:
        project = s.execute(select(Project)).scalars().first()
        deployments = (
            s.execute(select(Deployment).order_by(Deployment.created_at.desc()).limit(10))
             .scalars().all()
        )
    return render_template("dashboard.html", project=project, deployments=deployments)

@web_bp.get("/deploy/new")
def new_deployment():
    with SessionLocal() as s:
        project = s.execute(select(Project)).scalars().first()
    # Render the form that lets the user choose branch/tag/release
    return render_template("new_deployment.html", project=project)

@web_bp.post("/deploy")
def start_deployment():
    ref_type = request.form.get("ref_type")
    ref_name = request.form.get("ref_name")
    if not ref_type or not ref_name:
        flash("Please choose a branch, tag, or release.", "warning")
        return redirect(url_for("web.new_deployment"))

    # enqueue your job (adapt to your actual tasks API)
    # from capistack.jobs.tasks import run_deployment
    # jid = run_deployment.delay(ref_type=ref_type, ref_name=ref_name)

    # For now, just redirect to a placeholder detail page
    return redirect(url_for("web.deployment_detail", deployment_id="placeholder"))

@web_bp.get("/deployments/<deployment_id>")
def deployment_detail(deployment_id):
    with SessionLocal() as s:
        deployment = s.get(Deployment, deployment_id)
    return render_template("deployment_detail.html", deployment=deployment)

@web_bp.get("/settings")
def settings():
    # Mask secrets in the template; just show read-only config
    return render_template("settings.html")

@web_bp.get("/about")
def about():
    # Render the form that lets the user choose branch/tag/release
    return render_template("about.html")