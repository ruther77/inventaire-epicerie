<?php

declare(strict_types=1);

use Framework\Application\Application;
use Framework\Routing\Router;

require __DIR__ . '/autoload.php';

$app = new Application();
$app->boot();

$router = $app->router();

require base_path('routes/web.php');

return $app;
