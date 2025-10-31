<?php
require_once __DIR__ . '/../app.php';

$title = 'Panier';
include __DIR__ . '/../header.php';
?>
<div class="content-wrapper container">
    <div class="page-content">
        <section class="page-placeholder">
            <div class="page-placeholder__icon">
                <i class="bi bi-bag"></i>
            </div>
            <h1 class="h3 mb-3">Panier</h1>
            <p class="text-muted mb-3">Votre panier est en cours de conception. Vous pourrez bientôt y retrouver vos produits enregistrés et passer au paiement en toute simplicité.</p>
            <a class="btn btn-primary" href="<?= url_for('Customer/shop.php') ?>">Revenir au catalogue</a>
        </section>
    </div>
<?php include __DIR__ . '/footer.php'; ?>
