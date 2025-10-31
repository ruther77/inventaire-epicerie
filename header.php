<?php
require_once __DIR__ . '/app.php';
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
<html lang="fr">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= htmlspecialchars($customerTitle, ENT_QUOTES, 'UTF-8') ?> - JELLOULI</title>

    <link rel="stylesheet" href="<?= asset('assets/css/main/app.css') ?>">
    <link rel="shortcut icon" href="<?= asset('assets/images/logo/favicon.svg') ?>" type="image/x-icon">
    <link rel="shortcut icon" href="<?= asset('assets/images/logo/favicon.png') ?>" type="image/png">
    <link rel="stylesheet" href="<?= asset('Customer/style.css') ?>">

    <link rel="stylesheet" href="<?= asset('assets/css/shared/iconly.css') ?>">
    <script defer src="<?= asset('Customer/navigation.js') ?>"></script>
</head>

<body>
    <div id="app" class="app-shell">
        <div id="main" class="layout-horizontal">
            <header class="site-header mb-5">
                <div class="container">
                    <div class="site-header__bar">
                        <div class="site-header__start">
                            <button class="site-header__burger d-flex d-xl-none align-items-center justify-content-center" type="button" aria-expanded="false" aria-controls="mobileNavigation" data-mobile-toggle>
                                <span class="visually-hidden">Ouvrir le menu</span>
                                <i class="bi bi-list"></i>
                            </button>
                            <a class="site-header__logo" href="<?= url_for('Customer/home.php') ?>">
                                <img src="<?= asset('assets/images/logo/logo-jell.png') ?>" height="30" alt="Logo Jellouli">
                            </a>
                            <button class="btn btn-outline-primary d-none d-xl-inline-flex align-items-center" type="button" data-catalog-toggle aria-expanded="false" aria-controls="catalogPanel">
                                <i class="bi bi-grid me-2"></i>
                                Catalogue
                            </button>
                        </div>
                        <nav class="site-header__primary d-none d-md-flex align-items-center">
                            <a class="site-header__link" href="<?= url_for('Customer/home.php') ?>">
                                <i class="bi bi-house-door me-1"></i>
                                Accueil
                            </a>
                            <button class="site-header__link" type="button" data-search-toggle aria-expanded="false" aria-controls="globalSearch">
                                <i class="bi bi-search me-1"></i>
                                Recherche
                            </button>
                        </nav>
                        <div class="site-header__end">
                            <button class="btn btn-outline-primary d-xl-none" type="button" data-catalog-toggle aria-expanded="false" aria-controls="catalogPanel">
                                <i class="bi bi-grid"></i>
                                <span class="ms-2">Catalogue</span>
                            </button>
                            <button class="btn btn-icon" type="button" data-search-toggle aria-expanded="false" aria-controls="globalSearch">
                                <span class="visually-hidden">Ouvrir la recherche</span>
                                <i class="bi bi-search"></i>
                            </button>
                            <div class="dropdown site-header__utilities">
                                <button class="btn btn-icon d-flex align-items-center" id="userUtilities" data-bs-toggle="dropdown" aria-expanded="false">
                                    <span class="position-relative me-2">
                                        <i class="bi bi-bell"></i>
                                        <span class="badge rounded-pill bg-danger notification-dot" data-notification-indicator></span>
                                    </span>
                                    <div class="avatar avatar-md2">
                                        <img src="<?= asset('assets/images/faces/1.jpg') ?>" alt="Avatar client">
                                    </div>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end shadow-lg" aria-labelledby="userUtilities">
                                    <li class="dropdown-header text-muted text-uppercase">Zone rapide</li>
                                    <li>
                                        <a class="dropdown-item d-flex justify-content-between align-items-center" href="<?= url_for('Customer/cart.php') ?>">
                                            <span><i class="bi bi-bag me-2"></i>Panier</span>
                                            <span class="badge bg-primary rounded-pill" data-cart-count><?= $cartCount ?></span>
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item d-flex justify-content-between align-items-center" href="<?= url_for('Customer/favorites.php') ?>">
                                            <span><i class="bi bi-heart me-2"></i>Favoris</span>
                                            <span class="badge bg-danger rounded-pill" data-wishlist-count><?= $wishlistCount ?></span>
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/orders.php') ?>"><i class="bi bi-receipt-cutoff me-2"></i>Commandes</a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/profile.php') ?>"><i class="bi bi-person-circle me-2"></i>Profil</a>
                                    </li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li class="dropdown-header text-muted text-uppercase">Préférences</li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/settings.php') ?>"><i class="bi bi-gear me-2"></i>Paramètres</a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/support.php') ?>"><i class="bi bi-question-circle me-2"></i>Aide &amp; support</a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/dashboard.php') ?>"><i class="bi bi-kanban me-2"></i>Centre de contrôle</a>
                                    </li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li>
                                        <a class="dropdown-item" href="<?= url_for('Customer/logout.php') ?>"><i class="bi bi-box-arrow-right me-2"></i>Déconnexion</a>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
                <nav class="catalog-panel" id="catalogPanel" data-catalog-panel aria-hidden="true">
                    <div class="catalog-panel__inner container">
                        <div class="catalog-panel__header">
                            <div>
                                <h2 class="h5 mb-1">Explorer le catalogue</h2>
                                <p class="text-muted mb-0">Filtrez les catégories, repérez les promotions et épinglez vos vues favorites.</p>
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
                        <section class="pinned-categories" data-pinned-container>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h3 class="h6 mb-0">Vos sections épinglées</h3>
                                <button class="btn btn-link btn-sm text-decoration-none" type="button" data-clear-pins>
                                    <i class="bi bi-x-circle me-1"></i>Effacer
                                </button>
                            </div>
                            <p class="text-muted small" data-empty-message>Aucune section épinglée pour le moment.</p>
                            <div class="row g-3" data-pinned-list></div>
                        </section>
                        <div class="row g-4">
                            <?php foreach ($categoryList as $index => $cat): ?>
                                <?php
                                    $categoryName = $cat->get('n');
                                    $categoryUrl = url_for('Customer/shop.php?id=' . urlencode($categoryName));
                                    $badge = $badgeCycle[$index % count($badgeCycle)];
                                ?>
                                <div class="col-12 col-md-6 col-xl-4">
                                    <article class="catalog-card" data-category-card data-category-name="<?= htmlspecialchars($categoryName, ENT_QUOTES, 'UTF-8') ?>" data-category-url="<?= htmlspecialchars($categoryUrl, ENT_QUOTES, 'UTF-8') ?>">
                                        <div class="catalog-card__header">
                                            <a class="stretched-link" href="<?= $categoryUrl ?>">
                                                <h4 class="h6 mb-0"><?= htmlspecialchars($categoryName, ENT_QUOTES, 'UTF-8') ?></h4>
                                            </a>
                                            <span class="badge <?= htmlspecialchars($badge['class'], ENT_QUOTES, 'UTF-8') ?>"><?= htmlspecialchars($badge['label'], ENT_QUOTES, 'UTF-8') ?></span>
                                        </div>
                                        <p class="catalog-card__meta text-muted">Découvrez les nouveautés et promotions de cette catégorie.</p>
                                        <div class="catalog-card__actions">
                                            <a class="btn btn-sm btn-outline-primary" href="<?= $categoryUrl ?>">Voir les produits</a>
                                            <button class="btn btn-sm btn-outline-secondary" type="button" data-pin-toggle>
                                                <i class="bi bi-pin-angle"></i>
                                                <span class="ms-1">Épingler</span>
                                            </button>
                                        </div>
                                    </article>
                                </div>
                            <?php endforeach; ?>
                        </div>
                    </div>
                    <button class="catalog-panel__close btn btn-link" type="button" data-catalog-toggle>
                        <i class="bi bi-x-lg me-1"></i>Fermer
                    </button>
                </nav>
                <div class="catalog-backdrop" data-catalog-backdrop></div>
                <div class="global-search-overlay" id="globalSearch" data-global-search aria-hidden="true">
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
                        <form class="global-search-form" action="<?= url_for('Customer/shop.php') ?>" method="get" data-global-search-form>
                            <label class="visually-hidden" for="globalSearchInput">Recherche globale</label>
                            <div class="input-group input-group-lg">
                                <span class="input-group-text"><i class="bi bi-search"></i></span>
                                <input id="globalSearchInput" class="form-control" type="search" name="q" placeholder="Rechercher un produit, une marque ou une promotion" autocomplete="off" data-global-search-input>
                                <button class="btn btn-primary" type="submit">Rechercher</button>
                            </div>
                        </form>
                        <div class="global-search-actions">
                            <button class="btn btn-link px-0" type="button" data-save-search>
                                <i class="bi bi-bookmark-plus me-1"></i>Enregistrer cette recherche
                            </button>
                            <button class="btn btn-link text-danger px-0" type="button" data-clear-searches>
                                <i class="bi bi-trash me-1"></i>Effacer les recherches enregistrées
                            </button>
                        </div>
                        <div class="global-search-saved">
                            <h3 class="h6 mb-2">Recherches enregistrées</h3>
                            <div class="saved-search-chips" data-saved-searches data-placeholder="false"></div>
                            <p class="text-muted small" data-no-saved-search>Aucune recherche enregistrée pour le moment.</p>
                        </div>
                    </div>
                </div>
                <nav class="mobile-nav" id="mobileNavigation" data-mobile-nav aria-hidden="true">
                    <div class="mobile-nav__header">
                        <span>Menu</span>
                        <button class="btn btn-link text-decoration-none" type="button" data-mobile-toggle>
                            <i class="bi bi-x-lg me-1"></i>Fermer
                        </button>
                    </div>
                    <div class="mobile-nav__body">
                        <form class="mobile-nav__search" action="<?= url_for('Customer/shop.php') ?>" method="get">
                            <label class="visually-hidden" for="mobileSearch">Recherche mobile</label>
                            <div class="input-group">
                                <span class="input-group-text"><i class="bi bi-search"></i></span>
                                <input id="mobileSearch" class="form-control" type="search" name="q" placeholder="Rechercher un produit ou une catégorie">
                            </div>
                        </form>
                        <section class="mobile-nav__section">
                            <h3 class="mobile-nav__title">Actions rapides</h3>
                            <ul class="list-unstyled mb-0">
                                <li><a class="mobile-nav__link" href="<?= url_for('Customer/home.php') ?>"><i class="bi bi-house-door me-2"></i>Accueil</a></li>
                                <li><a class="mobile-nav__link" href="<?= url_for('Customer/shop.php') ?>"><i class="bi bi-grid me-2"></i>Explorer</a></li>
                                <li><a class="mobile-nav__link" href="<?= url_for('Customer/orders.php') ?>"><i class="bi bi-receipt-cutoff me-2"></i>Mes commandes</a></li>
                                <li><a class="mobile-nav__link" href="<?= url_for('Customer/support.php') ?>"><i class="bi bi-question-circle me-2"></i>Aide</a></li>
                            </ul>
                        </section>
                        <section class="mobile-nav__section">
                            <h3 class="mobile-nav__title">Catégories</h3>
                            <div class="mobile-nav__chips">
                                <?php foreach ($quickFilters as $filter): ?>
                                    <a class="mobile-chip" href="<?= $filter['url'] ?>"><?= htmlspecialchars($filter['label'], ENT_QUOTES, 'UTF-8') ?></a>
                                <?php endforeach; ?>
                            </div>
                        </section>
                        <section class="mobile-nav__section">
                            <h3 class="mobile-nav__title">Sections épinglées</h3>
                            <div class="mobile-nav__chips" data-pinned-mobile></div>
                            <p class="text-muted small" data-mobile-empty>Aucune section épinglée pour l'instant.</p>
                        </section>
                    </div>
                </nav>
                <div class="mobile-nav-backdrop" data-mobile-backdrop></div>
            </header>
