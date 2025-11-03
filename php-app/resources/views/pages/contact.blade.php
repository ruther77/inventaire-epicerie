@extends('layouts.app')

@section('title'){{ trans('messages.contact') }}@endsection

@section('content')
<section class="max-w-3xl mx-auto px-6 py-12">
    <h1 class="text-3xl font-semibold text-slate-900 mb-6">{{ trans('messages.contact_title') }}</h1>

    <form method="post" action="/contact" class="space-y-6">
        @csrf
        <div>
            <label class="block text-sm font-medium text-slate-700 mb-1" for="name">{{ trans('messages.name') }}</label>
            <input type="text" id="name" name="name" value="{{ old('name') }}" class="w-full border rounded-md px-3 py-2">
            @error('name')
                <p class="mt-2 text-sm text-red-600">{{ $__env->error('name') }}</p>
            @enderror
        </div>
        <div>
            <label class="block text-sm font-medium text-slate-700 mb-1" for="email">{{ trans('messages.email') }}</label>
            <input type="email" id="email" name="email" value="{{ old('email') }}" class="w-full border rounded-md px-3 py-2">
            @error('email')
                <p class="mt-2 text-sm text-red-600">{{ $__env->error('email') }}</p>
            @enderror
        </div>
        <div>
            <label class="block text-sm font-medium text-slate-700 mb-1" for="message">{{ trans('messages.message') }}</label>
            <textarea id="message" name="message" rows="5" class="w-full border rounded-md px-3 py-2">{{ old('message') }}</textarea>
            @error('message')
                <p class="mt-2 text-sm text-red-600">{{ $__env->error('message') }}</p>
            @enderror
        </div>
        <button type="submit" class="px-5 py-2 bg-emerald-600 text-white font-medium rounded-md hover:bg-emerald-700">{{ trans('messages.send_message') }}</button>
    </form>
</section>
@endsection
