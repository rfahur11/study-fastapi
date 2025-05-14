import socketio
from typing import Dict, Any

# Buat Socket.IO server dengan konfigurasi yang benar
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*'  # Gunakan string '*' untuk mengizinkan semua asal di lingkungan dev
)

# Buat ASGI app untuk Socket.IO - perbaiki konfigurasi
socket_app = socketio.ASGIApp(
    socketio_server=sio,
    # Hapus socketio_path di sini
)

# Simpan koneksi pengguna aktif
connected_users: Dict[str, Dict[str, Any]] = {}

# Peristiwa koneksi
@sio.event
async def connect(sid, environ):
    """Tangani koneksi socket baru"""
    print(f"Client connected: {sid}")
    connected_users[sid] = {"user_id": None}  # Inisialisasi, akan diupdate saat login

@sio.event
async def disconnect(sid):
    """Tangani disconnect socket"""
    print(f"Client disconnected: {sid}")
    if sid in connected_users:
        del connected_users[sid]

# Peristiwa autentikasi
@sio.event
async def authenticate(sid, data):
    """Autentikasi user dan simpan user_id ke connected_users"""
    if 'user_id' in data:
        user_id = data['user_id']
        connected_users[sid]['user_id'] = user_id
        print(f"User authenticated: {user_id} (sid: {sid})")
        return {"status": "authenticated"}
    return {"status": "error", "message": "Missing user_id"}

# Peristiwa untuk post baru
@sio.event
async def join_post_room(sid, data):
    """Bergabung ke room post untuk mendapatkan update real-time"""
    if 'post_id' in data:
        post_id = data['post_id']
        room = f"post_{post_id}"
        await sio.enter_room(sid, room)
        print(f"Client {sid} joined room: {room}")
        return {"status": "success"}
    return {"status": "error", "message": "Missing post_id"}

# Fungsi helper untuk broadcast update
async def broadcast_post_update(post_id, post_data, event_type="update"):
    """Kirim update post ke semua klien yang terhubung ke room post"""
    room = f"post_{post_id}"
    await sio.emit(
        'post_update',
        {
            'type': event_type,  # 'create', 'update', 'delete'
            'post_id': post_id,
            'data': post_data
        },
        room=room
    )

async def broadcast_post_list_update():
    """Kirim notifikasi bahwa daftar post telah berubah"""
    await sio.emit('posts_list_update', {})

async def broadcast_new_post(post_data):
    """Kirim notifikasi bahwa post baru telah dibuat"""
    await sio.emit(
        'new_post', 
        {
            'post': post_data
        }
    )

# Tambahkan event handler test sederhana
@sio.event
async def test_event(sid, data):
    """Event test sederhana"""
    print(f"Test event received from {sid}: {data}")
    return {"status": "success", "message": "Test event received"}

@sio.event
async def ping(sid):
    print(f"Ping from {sid}")
    return {"status": "pong", "timestamp": time.time()}