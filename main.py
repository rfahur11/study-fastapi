from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List, Optional
import json

from database import engine, get_db, check_database_connection, Base
import models
from schemas import UserCreate, UserResponse, PostCreate, PostResponse, PostUpdate
from sockets import socket_app, broadcast_post_update, broadcast_post_list_update, broadcast_new_post

app = FastAPI(title="FastAPI CRUD Demo")

# Mount Socket.IO app
app.mount("/socket.io", socket_app)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Jinja2Templates
templates = Jinja2Templates(directory="templates")

# Create tables on startup
@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        # Drop all tables (comment this out in production)
        # await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Render the home page template
    """
    return templates.TemplateResponse("index.html", {"request": request, "title": "FastAPI CRUD Demo"})

@app.get("/check-db")
async def check_db():
    """
    Endpoint to check if database connection is working.
    Returns status and message indicating success or failure.
    """
    return await check_database_connection()

# Web UI routes
@app.get("/web/users", response_class=HTMLResponse)
async def web_users_list(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Display users list web page
    """
    result = await db.execute(select(models.User))
    users = result.scalars().all()
    return templates.TemplateResponse("users/list.html", {
        "request": request, 
        "users": users,
        "title": "Users List"
    })

@app.get("/web/users/create", response_class=HTMLResponse)
async def web_create_user_form(request: Request):
    """
    Display user creation form
    """
    return templates.TemplateResponse("users/create.html", {
        "request": request,
        "title": "Create User"
    })

@app.post("/web/users/create", response_class=HTMLResponse)
async def web_create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    is_active: bool = Form(True),
    db: AsyncSession = Depends(get_db)
):
    """
    Process user creation form
    """
    # Check if username or email already exists
    result = await db.execute(select(models.User).filter(
        (models.User.username == username) | (models.User.email == email)
    ))
    existing_user = result.scalars().first()
    
    if existing_user:
        return templates.TemplateResponse(
            "users/create.html", 
            {
                "request": request,
                "title": "Create User",
                "error": "Username or email already registered",
                "username": username,
                "email": email,
                "is_active": is_active
            },
            status_code=400
        )
    
    # Create new user
    db_user = models.User(
        username=username,
        email=email,
        hashed_password=password,  # Should be hashed in production!
        is_active=is_active
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # Redirect to users list with success message
    response = RedirectResponse(url="/web/users", status_code=303)
    return response

@app.get("/web/posts", response_class=HTMLResponse)
async def web_posts_list(request: Request, format: str = None, db: AsyncSession = Depends(get_db)):
    """
    Display posts list web page or return JSON for API clients
    """
    # Get posts with author information
    query = select(models.Post, models.User.username).join(
        models.User, models.Post.author_id == models.User.id
    )
    result = await db.execute(query)
    posts_with_authors = result.all()
    
    # Return JSON if requested
    if format == "json":
        posts_data = []
        for post, author_name in posts_with_authors:
            posts_data.append({
                "id": post.id,
                "title": post.title,
                "author": author_name,
                "published": post.published,
                "created_at": post.created_at.isoformat(),
                "author_id": post.author_id
            })
        return JSONResponse({"posts": posts_data})
    
    # Otherwise return HTML template
    return templates.TemplateResponse("posts/list.html", {
        "request": request, 
        "posts": posts_with_authors,
        "title": "Posts List"
    })

@app.get("/web/posts/create", response_class=HTMLResponse)
async def web_create_post_form(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Display post creation form
    """
    # Get users for dropdown
    result = await db.execute(select(models.User))
    users = result.scalars().all()
    
    return templates.TemplateResponse("posts/create.html", {
        "request": request,
        "title": "Create Post",
        "users": users
    })

@app.post("/web/posts/create", response_class=HTMLResponse)
async def web_create_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    published: bool = Form(False),
    author_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Process post creation form
    """
    # Check if user exists
    user_result = await db.execute(select(models.User).filter(models.User.id == author_id))
    user = user_result.scalars().first()
    
    if not user:
        # Get users for dropdown
        result = await db.execute(select(models.User))
        users = result.scalars().all()
        
        return templates.TemplateResponse(
            "posts/create.html", 
            {
                "request": request,
                "title": "Create Post",
                "error": f"User with ID {author_id} not found",
                "post_title": title,
                "content": content,
                "published": published,
                "users": users
            },
            status_code=400
        )
    
    # Create new post
    db_post = models.Post(
        title=title,
        content=content,
        published=published,
        author_id=author_id
    )
    
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)
    
    # Convert post model to dict for broadcast via socket
    post_data = {
        "id": db_post.id,
        "title": db_post.title,
        "content": db_post.content,
        "published": db_post.published,
        "author_id": db_post.author_id,
        "created_at": db_post.created_at.isoformat()
    }
    
    # Broadcast update via Socket.IO
    await broadcast_new_post(post_data)
    await broadcast_post_list_update()
    
    # Redirect to posts list
    response = RedirectResponse(url="/web/posts", status_code=303)
    return response

@app.get("/web/posts/{post_id}", response_class=HTMLResponse)
async def web_post_detail(request: Request, post_id: int, db: AsyncSession = Depends(get_db)):
    """
    Display post detail page
    """
    # Get post with author information
    result = await db.execute(
        select(models.Post).filter(models.Post.id == post_id)
    )
    post = result.scalars().first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Get author
    author_result = await db.execute(
        select(models.User).filter(models.User.id == post.author_id)
    )
    author = author_result.scalars().first()
    
    return templates.TemplateResponse("posts/detail.html", {
        "request": request,
        "title": post.title,
        "post": post,
        "author": author
    })

@app.get("/web/posts/{post_id}/edit", response_class=HTMLResponse)
async def web_edit_post_form(request: Request, post_id: int, db: AsyncSession = Depends(get_db)):
    """
    Display post edit form
    """
    # Get post
    result = await db.execute(
        select(models.Post).filter(models.Post.id == post_id)
    )
    post = result.scalars().first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Get users for dropdown
    users_result = await db.execute(select(models.User))
    users = users_result.scalars().all()
    
    return templates.TemplateResponse("posts/edit.html", {
        "request": request,
        "title": f"Edit Post: {post.title}",
        "post": post,
        "users": users
    })

@app.post("/web/posts/{post_id}/edit", response_class=HTMLResponse)
async def web_update_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    content: str = Form(...),
    published: bool = Form(False),
    author_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Process post update form
    """
    # Check if post exists
    post_result = await db.execute(select(models.Post).filter(models.Post.id == post_id))
    post = post_result.scalars().first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user exists
    user_result = await db.execute(select(models.User).filter(models.User.id == author_id))
    user = user_result.scalars().first()
    
    if not user:
        # Get users for dropdown
        result = await db.execute(select(models.User))
        users = result.scalars().all()
        
        return templates.TemplateResponse(
            "posts/edit.html", 
            {
                "request": request,
                "title": f"Edit Post: {post.title}",
                "error": f"User with ID {author_id} not found",
                "post": post,
                "users": users
            },
            status_code=400
        )
    
    # Update post
    post.title = title
    post.content = content
    post.published = published
    post.author_id = author_id
    
    await db.commit()
    await db.refresh(post)
    
    # Convert post model to dict for broadcast via socket
    post_data = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "published": post.published,
        "author_id": post.author_id,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None
    }
    
    # Broadcast update via Socket.IO
    await broadcast_post_update(post_id, post_data, "update")
    
    # Redirect to post detail
    response = RedirectResponse(url=f"/web/posts/{post_id}", status_code=303)
    return response

@app.post("/web/posts/{post_id}/delete", response_class=HTMLResponse)
async def web_delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete post
    """
    # Check if post exists
    post_result = await db.execute(select(models.Post).filter(models.Post.id == post_id))
    post = post_result.scalars().first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Delete post
    await db.delete(post)
    await db.commit()
    
    # Broadcast delete via Socket.IO
    await broadcast_post_update(post_id, {}, "delete")
    await broadcast_post_list_update()
    
    # Redirect to posts list
    response = RedirectResponse(url="/web/posts", status_code=303)
    return response

# User CRUD operations
@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # In production, hash the password here
    hashed_password = user.password  # This should be hashed in production!
    
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_active=user.is_active
    )
    
    # Check if username or email already exists
    result = await db.execute(select(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@app.get("/users/", response_model=List[UserResponse])
async def read_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users

# Post CRUD operations
@app.post("/posts/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, user_id: int, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    user_result = await db.execute(select(models.User).filter(models.User.id == user_id))
    user = user_result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    db_post = models.Post(**post.dict(), author_id=user_id)
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)
    return db_post

@app.get("/posts/", response_model=List[PostResponse])
async def read_posts(
    skip: int = 0, 
    limit: int = 100, 
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(models.Post)
    
    if search:
        query = query.filter(models.Post.title.contains(search))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    posts = result.scalars().all()
    return posts

@app.get("/posts/{post_id}", response_model=PostResponse)
async def read_post(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Post).filter(models.Post.id == post_id))
    post = result.scalars().first()
    
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )
    
    return post

@app.put("/posts/{post_id}", response_model=PostResponse)
async def update_post(post_id: int, post: PostUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Post).filter(models.Post.id == post_id))
    db_post = result.scalars().first()
    
    if db_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )
    
    # Update only fields that are provided
    update_data = post.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_post, key, value)
    
    await db.commit()
    await db.refresh(db_post)
    return db_post

@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Post).filter(models.Post.id == post_id))
    post = result.scalars().first()
    
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )
    
    await db.delete(post)
    await db.commit()
    return None