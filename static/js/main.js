// Add any custom JavaScript functionality here
document.addEventListener('DOMContentLoaded', function() {
    console.log('FastAPI CRUD Demo Frontend Initialized');

    // Inisialisasi Socket.IO jika library tersedia
    if (typeof io !== 'undefined') {
        initializeSocketIO();
    }
});

function initializeSocketIO() {
    // Perbaikan: Konfigurasi koneksi Socket.IO yang benar
    const socket = io({
        transports: ['websocket'],
        upgrade: false
    });

    // Event saat berhasil terhubung
    socket.on('connect', () => {
        console.log('Connected to Socket.IO server with ID:', socket.id);
        
        // Test koneksi
        socket.emit('test_event', {message: 'Hello from client'}, (response) => {
            console.log('Server response:', response);
        });
        
        // Jika di halaman post list, aktifkan update real-time
        if (window.location.pathname === '/web/posts') {
            setupPostsListRealtime(socket);
        }
        
        // Jika di halaman detail post, aktifkan update real-time
        if (window.location.pathname.match(/^\/web\/posts\/\d+$/)) {
            const postId = parseInt(window.location.pathname.split('/').pop());
            setupPostDetailRealtime(socket, postId);
        }
    });

    // Event saat koneksi terputus
    socket.on('disconnect', (reason) => {
        console.log('Disconnected from Socket.IO server:', reason);
    });

    // Event saat terjadi error
    socket.on('connect_error', (error) => {
        console.error('Socket connection error:', error);
    });
}

function setupPostsListRealtime(socket) {
    // Listen untuk update daftar post
    socket.on('posts_list_update', () => {
        console.log('Posts list updated, refreshing...');
        refreshPostsList();
    });
    
    // Listen untuk post baru
    socket.on('new_post', (data) => {
        console.log('New post created:', data);
        addPostToList(data.post);
    });
}

function setupPostDetailRealtime(socket, postId) {
    // Bergabung ke room post untuk mendapatkan update
    socket.emit('join_post_room', { post_id: postId });
    
    // Listen untuk update post
    socket.on('post_update', (data) => {
        console.log('Post update received:', data);
        
        if (data.post_id === postId) {
            if (data.type === 'update') {
                updatePostDetails(data.data);
            } else if (data.type === 'delete') {
                handlePostDeleted();
            }
        }
    });
}

// Fungsi helper untuk merefresh daftar post tanpa reload halaman
function refreshPostsList() {
    // Gunakan fetch API untuk memuat ulang daftar post
    fetch('/web/posts?format=json')
        .then(response => response.json())
        .then(data => {
            updatePostsListUI(data.posts);
        })
        .catch(error => console.error('Error refreshing posts:', error));
}

// Fungsi untuk menambahkan post baru ke daftar tanpa reload
function addPostToList(post) {
    // Implementasi UI update
    const postsTable = document.querySelector('.table tbody');
    if (!postsTable) return;
    
    // Cek apakah post sudah ada
    const existingRow = document.querySelector(`tr[data-post-id="${post.id}"]`);
    if (existingRow) return;
    
    // Buat row baru untuk post
    const row = document.createElement('tr');
    row.setAttribute('data-post-id', post.id);
    
    // Isi row dengan data post
    const statusBadge = post.published ? 
        '<span class="badge bg-success">Published</span>' : 
        '<span class="badge bg-warning">Draft</span>';
    
    const date = new Date(post.created_at);
    const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    row.innerHTML = `
        <td>${post.id}</td>
        <td>${post.title}</td>
        <td>Unknown</td>
        <td>${statusBadge}</td>
        <td>${formattedDate}</td>
        <td>
            <div class="btn-group btn-group-sm" role="group">
                <a href="/web/posts/${post.id}" class="btn btn-info">View</a>
                <a href="/web/posts/${post.id}/edit" class="btn btn-warning">Edit</a>
                <button class="btn btn-danger" data-bs-toggle="modal" data-bs-target="#deleteModal${post.id}">Delete</button>
            </div>
            
            <!-- Delete Modal -->
            <div class="modal fade" id="deleteModal${post.id}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Confirm Delete</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            Are you sure you want to delete "${post.title}"? This action cannot be undone.
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <form action="/web/posts/${post.id}/delete" method="post">
                                <button type="submit" class="btn btn-danger">Delete</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </td>
    `;

    // Prepend row ke tabel
    if (postsTable.querySelector('tr')) {
        postsTable.insertBefore(row, postsTable.querySelector('tr'));
    } else {
        postsTable.appendChild(row);
    }
    
    // Jika baris "No posts found" ada, hapus
    const noPostsRow = postsTable.querySelector('tr td[colspan="6"]');
    if (noPostsRow) {
        noPostsRow.closest('tr').remove();
    }
}

// Fungsi untuk mengupdate detail post tanpa reload
function updatePostDetails(postData) {
    // Update title
    const titleElement = document.querySelector('.card-header h5');
    if (titleElement) titleElement.textContent = postData.title;
    
    // Update content
    const contentElement = document.querySelector('.post-content');
    if (contentElement) {
        contentElement.innerHTML = postData.content.replace(/\n/g, '<br>');
    }
    
    // Update status publikasi
    const statusBadge = document.querySelector('.badge');
    if (statusBadge) {
        if (postData.published) {
            statusBadge.textContent = 'Published';
            statusBadge.className = 'badge bg-success';
        } else {
            statusBadge.textContent = 'Draft';
            statusBadge.className = 'badge bg-warning';
        }
    }
}

// Fungsi untuk menangani post yang dihapus
function handlePostDeleted() {
    alert('This post has been deleted by another user.');
    window.location.href = '/web/posts';
}

// Tambahkan fungsi implementasi untuk updatePostsListUI
function updatePostsListUI(posts) {
    const postsTable = document.querySelector('.table tbody');
    if (!postsTable) return;
    
    // Bersihkan tabel
    postsTable.innerHTML = '';
    
    if (posts.length === 0) {
        postsTable.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">No posts found</td>
            </tr>
        `;
        return;
    }
    
    // Tambahkan semua post
    posts.forEach(post => {
        const statusBadge = post.published ? 
            '<span class="badge bg-success">Published</span>' : 
            '<span class="badge bg-warning">Draft</span>';
        
        const date = new Date(post.created_at);
        const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        const row = document.createElement('tr');
        row.setAttribute('data-post-id', post.id);
        
        row.innerHTML = `
            <td>${post.id}</td>
            <td>${post.title}</td>
            <td>${post.author}</td>
            <td>${statusBadge}</td>
            <td>${formattedDate}</td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <a href="/web/posts/${post.id}" class="btn btn-info">View</a>
                    <a href="/web/posts/${post.id}/edit" class="btn btn-warning">Edit</a>
                    <button class="btn btn-danger" data-bs-toggle="modal" data-bs-target="#deleteModal${post.id}">Delete</button>
                </div>
                
                <!-- Delete Modal -->
                <div class="modal fade" id="deleteModal${post.id}" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Confirm Delete</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                Are you sure you want to delete "${post.title}"? This action cannot be undone.
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <form action="/web/posts/${post.id}/delete" method="post">
                                    <button type="submit" class="btn btn-danger">Delete</button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </td>
        `;
        
        postsTable.appendChild(row);
    });
}