document.addEventListener('DOMContentLoaded', () => {
    const uploadBox = document.getElementById('uploadBox');
    const fileInput = document.getElementById('file-input');
    const pdfPreview = document.getElementById('pdf-preview');
    const uploadForm = document.getElementById('upload-form');
    
    if (uploadBox && fileInput && pdfPreview && uploadForm) {
        // File selection handling
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                handleFileSelection(e.target.files[0]);
            }
        });

        // Drag and drop handling
        uploadBox.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadBox.classList.add('dragover');
        });

        uploadBox.addEventListener('dragleave', () => {
            uploadBox.classList.remove('dragover');
        });

        uploadBox.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadBox.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                handleFileSelection(e.dataTransfer.files[0]);
                fileInput.files = e.dataTransfer.files;
            }
        });

        // Form submission - just show loading state
        uploadForm.addEventListener('submit', () => {
            const submitButton = uploadForm.querySelector('.submit-button');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            }
        });
    }
    // Function to handle file selection
    function handleFileSelection(file) {
        if (file.type === 'application/pdf') {
            const fileURL = URL.createObjectURL(file);
            pdfPreview.src = fileURL;
            pdfPreview.style.display = 'block';
            uploadBox.querySelector('img').style.display = 'none';
            uploadBox.querySelector('p').style.display = 'none';
            uploadBox.querySelector('.pdf-instruction').style.display = 'none';
        } else {
            showError('Only PDF files are allowed!');
        }
    }
    // Function to show error message`
    function showError(message) {
        const existingError = document.querySelector('.error-message');
        if (existingError) existingError.remove();
        
        const errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        errorElement.style.color = 'red';
        errorElement.style.marginTop = '10px';
        errorElement.textContent = message;
        
        uploadForm.appendChild(errorElement);
        
        setTimeout(() => errorElement.remove(), 5000);
    }
});