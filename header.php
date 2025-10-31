<?php
require_once __DIR__ . '/../../config/app.php';
require_once APP_ROOT . '/DAO/DAO.php';
require_once APP_ROOT . '/Metier/categorie.php';

$customerTitle = $title ?? 'JELLOULI';
$categoryList = Categorie::afficher();
$badgeCycle = [
    ['label' => 'Top ventes', 'class' => 'badge-top'],
    ['label' => 'Promo', 'class' => 'badge-promo'],
    ['label' => 'Nouveau', 'class' => 'badge-new'],
];

$quickFilters = array_slice(array_map(static function ($category) {
    return [
        'label' => $category->get('n'),
        'url' => url_for('Customer/shop.php?id=' . urlencode($category->get('n'))),
    ];
}, $categoryList), 0, 6);

$cartCount = isset($_SESSION['cart_items']) && is_array($_SESSION['cart_items']) ? count($_SESSION['cart_items']) : 0;
$wishlistCount = isset($_SESSION['wishlist']) && is_array($_SESSION['wishlist']) ? count($_SESSION['wishlist']) : 0;
?>
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= htmlspecialchars($customerTitle, ENT_QUOTES, 'UTF-8') ?> - JELLOULI</title>

    <link rel="stylesheet" href="<?= asset('assets/css/main/app.css') ?>">
    <link rel="shortcut icon" href="<?= asset('assets/images/logo/favicon.svg') ?>" type="image/x-icon">
    <link rel="shortcut icon" href="<?= asset('assets/images/logo/favicon.png') ?>" type="image/png">
    <link href="<?= asset('Customer/style.css') ?>" rel="stylesheet">

    <link rel="stylesheet" href="<?= asset('assets/css/shared/iconly.css') ?>">
    <script defer src="<?= asset('Customer/navigation.js') ?>"></script>

</head>

<body>
    <div id="app" style="background-color: #F5F5F9;">
        <div id="main" class="layout-horizontal">
            <header class="mb-5 site-header">
                <div class="container">
                    <div class="header-bar d-flex align-items-center justify-content-between">
                        <div class="d-flex align-items-center gap-3">
                            <button class="burger-btn d-flex d-xl-none align-items-center justify-content-center" type="button" aria-expanded="false" aria-controls="mobileNavigation" data-mobile-toggle>
                                <span class="visually-hidden">Ouvrir le menu</span>
                                <i class="bi bi-list"></i>
                            </button>
                            <a class="logo" href="<?= url_for('Customer/home.php') ?>">
                                <img src="<?= asset('assets/images/logo/logo-jell.png') ?>" height="30" alt="Logo Jellouli">
                            </a>
                            <button class="btn btn-outline-primary catalog-trigger d-none d-xl-flex align-items-center" type="button" data-catalog-toggle aria-expanded="false" aria-controls="catalogPanel">
                                <i class="bi bi-grid me-2"></i>
                                Catalogue
                            </button>
                        </div>
                        <ul class="primary-actions list-unstyled d-none d-xl-flex align-items-center mb-0">
                            <li>
                                <a class="action-link" href="<?= url_for('Customer/home.php') ?>">
                                    <i class="bi bi-house-door me-1"></i>
                                    Accueil
                                </a>
                            </li>
                            <li>
                                <button class="action-link" type="button" data-search-toggle aria-expanded="false" aria-controls="globalSearch">
                                    <i class="bi bi-search me-1"></i>
                                    Recherche
                                </button>
                            </li>
                        </ul>
                        <div class="header-utilities d-flex align-items-center gap-2">
                            <button class="btn btn-outline-primary catalog-trigger d-xl-none" type="button" data-catalog-toggle aria-expanded="false" aria-controls="catalogPanel">
                                <i class="bi bi-grid"></i>
                                <span class="ms-2">Catalogue</span>
                            </button>
                            <button class="btn btn-icon" type="button" data-search-toggle aria-expanded="false" aria-controls="globalSearch">
                                <span class="visually-hidden">Rechercher</span>
                                <i class="bi bi-search"></i>
                            </button>
                            <div class="dropdown user-utilities">
                                <button class="btn btn-icon user-toggle d-flex align-items-center" id="topbarUserDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                                    <span class="position-relative me-2">
                                        <i class="bi bi-bell"></i>
                                        <span class="badge rounded-pill bg-danger notification-dot" data-notification-indicator></span>
                                    </span>
                                    <div class="avatar avatar-md2">
                                        <img src="<?= asset('assets/images/faces/1.jpg') ?>" alt="Avatar">
                                    </div>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end shadow-lg" aria-labelledby="topbarUserDropdown">
                                    <li class="dropdown-header text-uppercase text-muted">Accès rapide</li>
                                    <li>
                                        <a class="dropdown-item d-flex align-items-center justify-content-between" href="<?= url_for('Customer/cart.php') ?>">
                                            <span><i class="bi bi-bag-check me-2"></i>Panier</span>
                                            <span class="badge bg-primary rounded-pill" data-cart-count><?= $cartCount ?></span>
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item d-flex align-items-center justify-content-between" href="<?= url_for('Customer/favorites.php') ?>">
                                            <span><i class="bi bi-heart me-2"></i>Favoris</span>
                                            <span class="badge bg-danger rounded-pill" data-wishlist-count><?= $wishlistCount ?></span>
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/profile.php') ?>"><i class="bi bi-person-circle me-2"></i>Profil</a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/orders.php') ?>"><i class="bi bi-receipt-cutoff me-2"></i>Commandes</a>
                                    </li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li class="dropdown-header text-uppercase text-muted">Paramètres</li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/settings.php') ?>"><i class="bi bi-gear me-2"></i>Préférences</a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/support.php') ?>"><i class="bi bi-question-circle me-2"></i>Aide & support</a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/logout.php') ?>"><i class="bi bi-box-arrow-right me-2"></i>Déconnexion</a>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
                <nav class="catalog-panel" id="catalogPanel" aria-hidden="true">
                    <div class="container">
                        <div class="catalog-panel__header d-flex flex-column flex-xl-row align-items-xl-center justify-content-between gap-3">
                            <div>
                                <h2 class="h5 mb-1">Explorer le catalogue</h2>
                                <p class="text-muted mb-0">Filtrez rapidement les catégories ou épinglez vos sections favorites.</p>
                            </div>
                            <div class="catalog-quick-filters">
                                <?php foreach ($quickFilters as $filter): ?>
                                    <a class="filter-chip" href="<?= $filter['url'] ?>">
                                        <i class="bi bi-funnel me-1"></i>
                                        <?= htmlspecialchars($filter['label'], ENT_QUOTES, 'UTF-8') ?>
                                    </a>
                                <?php endforeach; ?>
                            </div>
                        </div>
                        <div class="catalog-panel__body">
                            <div class="pinned-categories" data-pinned-container>
                                <div class="d-flex align-items-center justify-content-between mb-2">
                                    <h3 class="h6 mb-0">Vos sections épinglées</h3>
                                    <button class="btn btn-link btn-sm text-decoration-none" type="button" data-clear-pins>
                                        <i class="bi bi-x-circle me-1"></i>Effacer
                                    </button>
                                </div>
                                <p class="text-muted small" data-empty-message>Aucune section épinglée pour le moment.</p>
                                <div class="row g-3" data-pinned-list></div>
                            </div>
                            <div class="row g-4">
                                <?php foreach ($categoryList as $index => $cat): ?>
                                    <?php $badge = $badgeCycle[$index % count($badgeCycle)]; ?>
                                    <div class="col-12 col-md-6 col-xl-4">
                                        <article class="catalog-card" data-category-name="<?= htmlspecialchars($cat->get('n'), ENT_QUOTES, 'UTF-8') ?>">
                                            <div class="catalog-card__header d-flex align-items-center justify-content-between">
                                                <a class="stretched-link" href="<?= url_for('Customer/shop.php?id=' . urlencode($cat->get('n'))) ?>">
                                                    <h4 class="h6 mb-0"><?= htmlspecialchars($cat->get('n'), ENT_QUOTES, 'UTF-8') ?></h4>
                                                </a>
                                                <span class="badge <?= htmlspecialchars($badge['class'], ENT_QUOTES, 'UTF-8') ?>"><?= htmlspecialchars($badge['label'], ENT_QUOTES, 'UTF-8') ?></span>
                                            </div>
                                            <p class="catalog-card__meta text-muted mb-3">Découvrez les nouveautés, promotions et meilleures ventes de cette famille de produits.</p>
                                            <div class="catalog-card__actions d-flex align-items-center justify-content-between">
                                                <a class="btn btn-sm btn-outline-primary" href="<?= url_for('Customer/shop.php?id=' . urlencode($cat->get('n'))) ?>">
                                                    Voir les produits
                                                </a>
                                                <button class="btn btn-sm btn-outline-secondary pin-toggle" type="button" aria-pressed="false" data-pin-toggle>
                                                    <i class="bi bi-pin-angle"></i>
                                                    <span class="ms-1">Épingler</span>
                                                </button>
                                            </div>
                                        </article>
                                    </div>
                                <?php endforeach; ?>
                            </div>
                        </div>
                    </div>
                    <button class="catalog-panel__close btn btn-link" type="button" data-catalog-toggle>
                        <i class="bi bi-x-lg me-1"></i>Fermer
                    </button>
                </nav>
                <div class="catalog-backdrop" data-catalog-backdrop></div>
                <div class="global-search-overlay" id="globalSearch" aria-hidden="true">
                    <div class="global-search-overlay__inner container">
                        <div class="d-flex justify-content-between align-items-start mb-4">
                            <div>
                                <h2 class="h4 mb-1">Rechercher dans l'épicerie</h2>
                                <p class="text-muted mb-0">Produits, catégories ou promotions en un clin d'œil.</p>
                            </div>
                            <button class="btn btn-link text-decoration-none" type="button" data-search-toggle>
                                <i class="bi bi-x-lg me-1"></i>
                                Fermer
                            </button>
                        </div>
                        <form class="global-search-form" action="<?= url_for('Customer/shop.php') ?>" method="get">
                            <label class="visually-hidden" for="globalSearchInput">Rechercher</label>
                            <div class="input-group input-group-lg">
                                <span class="input-group-text"><i class="bi bi-search"></i></span>
                                <input id="globalSearchInput" class="form-control" type="search" name="q" placeholder="Chercher un produit, une catégorie…" autocomplete="off">
                                <button class="btn btn-primary" type="submit">Rechercher</button>
                            </div>
                        </form>
                        <div class="global-search-suggestions mt-4">
                            <h3 class="h6 text-uppercase text-muted mb-3">Suggestions</h3>
                            <div class="row g-3">
                                <?php foreach ($quickFilters as $filter): ?>
                                    <div class="col-12 col-md-6 col-xl-4">
                                        <a class="suggestion-tile" href="<?= $filter['url'] ?>">
                                            <span class="suggestion-title"><?= htmlspecialchars($filter['label'], ENT_QUOTES, 'UTF-8') ?></span>
                                            <span class="suggestion-meta">Voir les articles correspondants</span>
                                        </a>
                                    </div>
                                <?php endforeach; ?>
                            </div>
                        </div>
                        <div class="global-search-saved mt-4">
                            <div class="d-flex align-items-center justify-content-between mb-2">
                                <h3 class="h6 text-uppercase text-muted mb-0">Recherches enregistrées</h3>
                                <div class="d-flex align-items-center gap-2">
                                    <button class="btn btn-sm btn-outline-secondary" type="button" data-save-search>
                                        <i class="bi bi-bookmark-plus me-1"></i>Enregistrer la recherche
                                    </button>
                                    <button class="btn btn-link btn-sm text-decoration-none" type="button" data-clear-searches>
                                        Effacer tout
                                    </button>
                                </div>
                            </div>
                            <p class="text-muted small" data-no-saved-search>Aucune recherche enregistrée pour le moment.</p>
                            <div class="saved-searches" data-saved-searches></div>
                        </div>
                    </div>
                </div>
                <div class="mobile-nav-overlay" id="mobileNavigation" aria-hidden="true">
                    <div class="mobile-nav-overlay__inner">
                        <div class="mobile-nav-header d-flex align-items-center justify-content-between">
                            <div class="d-flex align-items-center gap-2">
                                <div class="avatar avatar-md2">
                                    <img src="<?= asset('assets/images/faces/1.jpg') ?>" alt="Avatar">
                                </div>
                                <div>
                                    <p class="mb-0 fw-semibold">Bonjour !</p>
                                    <small class="text-muted">Retrouvez vos espaces en un geste.</small>
                                </div>
                            </div>
                            <button class="btn btn-link text-decoration-none" type="button" data-mobile-toggle>
                                <i class="bi bi-x-lg"></i>
                            </button>
                        </div>
                        <form class="mobile-search mt-3" action="<?= url_for('Customer/shop.php') ?>" method="get">
                            <div class="input-group">
                                <span class="input-group-text"><i class="bi bi-search"></i></span>
                                <input class="form-control" type="search" name="q" placeholder="Rechercher un article…">
                            </div>
                        </form>
                        <div class="mobile-links mt-4">
                            <a class="mobile-link" href="<?= url_for('Customer/home.php') ?>"><i class="bi bi-house-door me-2"></i>Accueil</a>
                            <button class="mobile-link" type="button" data-catalog-toggle><i class="bi bi-grid me-2"></i>Catalogue</button>
                            <a class="mobile-link" href="<?= url_for('Customer/cart.php') ?>"><i class="bi bi-bag-check me-2"></i>Panier</a>
                            <a class="mobile-link" href="<?= url_for('Customer/favorites.php') ?>"><i class="bi bi-heart me-2"></i>Favoris</a>
                            <a class="mobile-link" href="<?= url_for('Customer/profile.php') ?>"><i class="bi bi-person-circle me-2"></i>Profil</a>
                        </div>
                        <div class="mobile-catalog mt-4">
                            <h3 class="h6 text-uppercase text-muted">Catégories</h3>
                            <div class="list-group">
                                <?php foreach ($categoryList as $index => $cat): ?>
                                    <?php $badge = $badgeCycle[$index % count($badgeCycle)]; ?>
                                    <a class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" href="<?= url_for('Customer/shop.php?id=' . urlencode($cat->get('n'))) ?>">
                                        <span><?= htmlspecialchars($cat->get('n'), ENT_QUOTES, 'UTF-8') ?></span>
                                        <span class="badge <?= htmlspecialchars($badge['class'], ENT_QUOTES, 'UTF-8') ?>"><?= htmlspecialchars($badge['label'], ENT_QUOTES, 'UTF-8') ?></span>
                                    </a>
                                <?php endforeach; ?>
                            </div>
                        </div>
                    </div>
                </div>
            </header>