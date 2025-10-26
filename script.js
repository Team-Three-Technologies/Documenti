document.addEventListener('DOMContentLoaded', function () {
    const folderHeaders = document.querySelectorAll('.folder-header');

    folderHeaders.forEach(header => {
        header.addEventListener('click', function () {
            const folderItem = this.parentElement;
            const folderContent = folderItem.querySelector('ul');

            if (folderContent) {
                folderItem.classList.toggle('collapsed');
                folderContent.classList.toggle('collapsed');
            }
        });
    });
});