<?php

declare(strict_types=1);

$_SERVER['REQUEST_METHOD'] = 'GET';
$_SERVER['REQUEST_URI'] = '/';
$_GET = [];
$_POST = [];

$app = require __DIR__ . '/../bootstrap/app.php';
$response = $app->handle();
$content = $response->getContent();

if (strpos($content, 'Inventaire Épicerie') === false) {
    fwrite(STDERR, "Page d'accueil introuvable" . PHP_EOL);
    exit(1);
}

echo "Smoke test OK" . PHP_EOL;
