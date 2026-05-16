/**
 * Toggle reference panel visibility when a publication row is clicked.
 * Dash serves this automatically from the assets/ directory.
 */
document.addEventListener('click', function(e) {
    // Find the closest pub-row ancestor
    var row = e.target.closest('.pub-row');
    if (!row) return;

    // Don't toggle if clicking on a button (copy, sort, etc.)
    if (e.target.closest('button') || e.target.closest('a')) return;

    // Find the pub-ref div inside this row
    var ref = row.querySelector('.pub-ref');
    if (!ref) return;

    // Toggle the 'show' class
    ref.classList.toggle('show');
});
