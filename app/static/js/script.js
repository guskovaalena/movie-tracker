document.addEventListener('DOMContentLoaded', function () {
    
    var modal = document.getElementById('deleteModal');
    var cancelBtn = document.getElementById('modalCancel');
    var confirmBtn = document.getElementById('modalConfirm');
    var currentForm = null;
    
    if (!modal || !cancelBtn || !confirmBtn) {
        console.log('Modal elements not found');
        return;
    }
    
    function openModal(form) {
        currentForm = form;
        modal.classList.add('active');
    }
    
    function closeModal() {
        modal.classList.remove('active');
        currentForm = null;
    }
    
    var deleteForms = document.querySelectorAll('.delete-form');
    console.log('Found delete forms:', deleteForms.length);
    
    deleteForms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            openModal(form);
        });
    });
    
    cancelBtn.addEventListener('click', function() {
        closeModal();
    });
    
    confirmBtn.addEventListener('click', function() {
        if (currentForm) {
            currentForm.submit();
        }
        closeModal();
    });
    
    modal.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModal();
        }
    });
    
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });
    
});