<?php

declare(strict_types=1);

use Framework\Application\Application;

$app = require __DIR__ . '/../bootstrap/app.php';

$response = $app->handle();
$response->send();
