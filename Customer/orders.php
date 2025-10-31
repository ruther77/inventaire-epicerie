<?php
require_once __DIR__ . '/../app.php';

$title = 'Mes commandes';
include __DIR__ . '/../header.php';
?>
<div class="content-wrapper container">
    <div class="page-content">
        <section class="page-placeholder">
            <div class="page-placeholder__icon">
                <i class="bi bi-receipt-cutoff"></i>
            </div>
            <h1 class="h3 mb-3">Mes commandes</h1>
            <p class="text-muted mb-3">Suivez vos achats depuis un espace centralisé. L'historique détaillé des commandes sera bientôt disponible ici.</p>
            <a class="btn btn-primary" href="<?= url_for('Customer/home.php') ?>">Retour à l'accueil</a>
        </section>
    </div>
<?php include __DIR__ . '/footer.php'; ?>
