<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use Framework\Http\Response;
use Framework\Validation\Validator;

final class ContactController extends Controller
{
    public function create(): Response
    {
        return $this->view('pages.contact');
    }

    public function store(): Response
    {
        $data = $this->request()->only(['name', 'email', 'message']);
        if (!$this->session()->validateCsrf($this->request()->input('_token'))) {
            return response('CSRF token mismatch', 419);
        }
        $validator = new Validator($data);
        $errors = $validator->validate([
            'name' => 'required|min:3',
            'email' => 'required|email',
            'message' => 'required|min:10',
        ]);

        if ($errors !== []) {
            $this->session()->setErrors($errors);
            $this->session()->setOld($data);

            return redirect('/contact');
        }

        $this->session()->flash('status', trans('messages.contact_received', ['name' => $data['name']]));
        $this->session()->setOld([]);
        $this->session()->setErrors([]);

        return redirect('/contact');
    }
}
