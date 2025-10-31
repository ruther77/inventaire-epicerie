<?php
require_once __DIR__ . '/../app.php';

$title = 'Favoris';
include __DIR__ . '/../header.php';
?>
<div class="content-wrapper container">
    <div class="page-content">
        <section class="page-placeholder">
            <div class="page-placeholder__icon">
                <i class="bi bi-heart"></i>
            </div>
            <h1 class="h3 mb-3">Favoris</h1>
            <p class="text-muted mb-3">Épinglez vos produits et catégories préférés. Ce module vous permettra bientôt de retrouver vos favoris en un clin d'œil.</p>
            <a class="btn btn-primary" href="<?= url_for('Customer/shop.php') ?>">Explorer les produits</a>
        </section>
    </div>
<?php include __DIR__ . '/footer.php'; ?>
