<?php

declare(strict_types=1);

namespace Framework\Application;

use Framework\Http\Request;
use Framework\Http\Response;
use Framework\I18n\Translator;
use Framework\Routing\Router;
use Framework\Support\Container;
use Framework\View\ViewFactory;
use Framework\Support\Session;

class Application
{
    private static ?self $instance = null;

    private Container $container;

    private Router $router;

    private Request $request;

    private Session $session;

    public function __construct()
    {
        $this->container = new Container();
        $this->request = Request::capture();
        $this->session = new Session();

        $this->container->singleton(self::class, fn () => $this);
        $this->container->singleton(Request::class, fn () => $this->request);
        $this->container->singleton(Session::class, fn () => $this->session);

        static::$instance = $this;
    }

    public static function getInstance(): self
    {
        if (!static::$instance) {
            throw new \RuntimeException('Application has not been bootstrapped.');
        }

        return static::$instance;
    }

    public function boot(): void
    {
        $config = require config_path('app.php');
        $this->container->singleton('config', fn () => $config);

        $this->container->singleton(ViewFactory::class, function (): ViewFactory {
            return new ViewFactory(resource_path('views'), storage_path('cache/views'));
        });

        $sessionLocale = $this->session->locale() ?? $config['locale'] ?? 'en';
        $fallback = $config['fallback_locale'] ?? 'en';

        $this->container->singleton(Translator::class, function () use ($sessionLocale, $fallback): Translator {
            $translator = new Translator(resource_path('lang'));
            $translator->setFallback($fallback);
            $translator->setLocale($sessionLocale);

            return $translator;
        });

        $this->router = new Router($this->container);
        $this->container->singleton(Router::class, fn () => $this->router);
    }

    public function handle(): Response
    {
        return $this->router->dispatch($this->request);
    }

    public function get(string $key): mixed
    {
        return $this->container->get($key);
    }

    public function router(): Router
    {
        return $this->router;
    }

    public function request(): Request
    {
        return $this->request;
    }

    public function session(): Session
    {
        return $this->session;
    }
}
