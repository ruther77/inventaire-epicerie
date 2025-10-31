<?php
require_once __DIR__ . '/../app.php';

$title = 'Aide & support';
include __DIR__ . '/../header.php';
?>
<div class="content-wrapper container">
    <div class="page-content">
        <section class="page-placeholder">
            <div class="page-placeholder__icon">
                <i class="bi bi-question-circle"></i>
            </div>
            <h1 class="h3 mb-3">Aide &amp; support</h1>
            <p class="text-muted mb-3">Besoin d'assistance ? Nous préparons une base de connaissances et un centre de contact pour répondre rapidement à vos demandes.</p>
            <a class="btn btn-primary" href="<?= url_for('Customer/home.php') ?>">Retour à l'accueil</a>
        </section>
    </div>
<?php include __DIR__ . '/footer.php'; ?>
