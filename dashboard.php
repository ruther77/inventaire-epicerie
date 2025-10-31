<?php
require_once __DIR__ . '/app.php';
require_once APP_ROOT . '/DAO/DAO.php';
require_once APP_ROOT . '/Metier/categorie.php';
require_once APP_ROOT . '/Metier/produit.php';

$title = 'Centre de contrôle';
$dao = new DAO();
$lowStockProducts = $dao->getTrendingProducts(3);
$categorySections = Categorie::afficher();

include __DIR__ . '/pages/header.php';
?>

<div class="content-wrapper container">
    <div class="page-content dashboard-page">
        <nav aria-label="breadcrumb" class="breadcrumb-wrapper">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="<?= url_for('Customer/home.php') ?>">Accueil</a></li>
                <li class="breadcrumb-item active" aria-current="page">Centre de contrôle</li>
            </ol>
        </nav>
        <header class="dashboard-page__header">
            <div>
                <h1 class="h3 mb-1">Pilotage opérationnel</h1>
                <p class="text-muted mb-0">Organisez votre inventaire, vos commandes et vos analyses depuis une page unique.</p>
            </div>
            <div class="d-flex align-items-center gap-2">
                <button class="btn btn-outline-secondary" type="button" data-search-toggle>
                    <i class="bi bi-search me-1"></i> Rechercher un produit
                </button>
                <a class="btn btn-primary" href="<?= url_for('Customer/shop.php') ?>">Passer à la boutique</a>
            </div>
        </header>

        <section id="inventory" class="dashboard-section">
            <div class="dashboard-section__header">
                <div>
                    <h2 class="h5 mb-1">Inventaire</h2>
                    <p class="text-muted mb-0">Suivez les niveaux de stock et planifiez vos réassorts.</p>
                </div>
                <div class="dashboard-section__actions">
                    <a class="btn btn-outline-primary btn-sm" href="#">Importer un catalogue</a>
                    <a class="btn btn-outline-secondary btn-sm" href="#">Exporter</a>
                </div>
            </div>
            <div class="row g-4">
                <?php foreach ($lowStockProducts as $product): ?>
                    <div class="col-12 col-md-4">
                        <article class="dashboard-tile">
                            <h3 class="h6 mb-1"><?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?></h3>
                            <p class="text-muted small mb-2">Référence : <?= htmlspecialchars($product->get('r'), ENT_QUOTES, 'UTF-8') ?></p>
                            <p class="mb-3">Stock estimé : <span class="fw-semibold"><?= number_format((float) $product->get('p'), 0, '.', ' ') ?></span> unités</p>
                            <div class="d-flex justify-content-between align-items-center">
                                <button class="btn btn-sm btn-outline-primary">Commander</button>
                                <button class="btn btn-sm btn-link text-decoration-none">Voir la fiche</button>
                            </div>
                        </article>
                    </div>
                <?php endforeach; ?>
            </div>
        </section>

        <section id="orders" class="dashboard-section">
            <div class="dashboard-section__header">
                <div>
                    <h2 class="h5 mb-1">Commandes</h2>
                    <p class="text-muted mb-0">Visualisez les commandes en cours et vos priorités de préparation.</p>
                </div>
                <div class="dashboard-section__actions">
                    <a class="btn btn-outline-primary btn-sm" href="#">Créer une commande</a>
                </div>
            </div>
            <div class="dashboard-kanban">
                <div class="dashboard-column">
                    <h3 class="dashboard-column__title">À préparer</h3>
                    <ul class="dashboard-column__list">
                        <li class="dashboard-column__item">Commande #4587 &middot; 4 articles &middot; Livraison demain</li>
                        <li class="dashboard-column__item">Commande #4588 &middot; 2 articles &middot; Retrait magasin</li>
                    </ul>
                </div>
                <div class="dashboard-column">
                    <h3 class="dashboard-column__title">En cours</h3>
                    <ul class="dashboard-column__list">
                        <li class="dashboard-column__item">Commande #4582 &middot; Emballage</li>
                        <li class="dashboard-column__item">Commande #4579 &middot; En tournée</li>
                    </ul>
                </div>
                <div class="dashboard-column">
                    <h3 class="dashboard-column__title">Terminées</h3>
                    <ul class="dashboard-column__list">
                        <li class="dashboard-column__item">Commande #4575 &middot; Livrée</li>
                        <li class="dashboard-column__item">Commande #4571 &middot; Livrée</li>
                    </ul>
                </div>
            </div>
        </section>

        <section id="analytics" class="dashboard-section">
            <div class="dashboard-section__header">
                <div>
                    <h2 class="h5 mb-1">Analyses</h2>
                    <p class="text-muted mb-0">Surveillez les indicateurs clés pour anticiper les tendances.</p>
                </div>
                <div class="dashboard-section__actions">
                    <button class="btn btn-outline-secondary btn-sm" type="button">Exporter le rapport</button>
                </div>
            </div>
            <div class="row g-4">
                <div class="col-12 col-md-4">
                    <div class="metric-card">
                        <p class="metric-card__label">Chiffre d'affaires (7 derniers jours)</p>
                        <p class="metric-card__value">52 400 Dhs</p>
                        <span class="metric-card__trend positive"><i class="bi bi-arrow-up"></i> +8%</span>
                    </div>
                </div>
                <div class="col-12 col-md-4">
                    <div class="metric-card">
                        <p class="metric-card__label">Panier moyen</p>
                        <p class="metric-card__value">430 Dhs</p>
                        <span class="metric-card__trend neutral"><i class="bi bi-dash"></i> Stable</span>
                    </div>
                </div>
                <div class="col-12 col-md-4">
                    <div class="metric-card">
                        <p class="metric-card__label">Produits en promotion</p>
                        <p class="metric-card__value">18</p>
                        <span class="metric-card__trend negative"><i class="bi bi-arrow-down"></i> -3% vs semaine passée</span>
                    </div>
                </div>
            </div>
        </section>

        <section class="dashboard-section">
            <div class="dashboard-section__header">
                <div>
                    <h2 class="h5 mb-1">Catégories clés</h2>
                    <p class="text-muted mb-0">Gardez un œil sur les familles prioritaires.</p>
                </div>
            </div>
            <div class="row g-3">
                <?php foreach (array_slice($categorySections, 0, 6) as $category): ?>
                    <div class="col-12 col-md-4 col-xl-2">
                        <a class="category-chip" href="<?= url_for('Customer/shop.php?id=' . urlencode($category->get('n'))) ?>">
                            <?= htmlspecialchars($category->get('n'), ENT_QUOTES, 'UTF-8') ?>
                        </a>
                    </div>
                <?php endforeach; ?>
            </div>
        </section>
    </div>

    <?php include __DIR__ . '/Customer/footer.php'; ?>
