% include header.tpl {"session_status": session_status}
<div class="container">
    <div class="row">
        <div class="col-md-6 col-centered">
            You'll need to authorize this app to use your Google account.  Please visit: <a href="{{oauth_uri}}">this url</a> and paste the key you receive here:
            <form class="form-horizontal well" name="auth" method="POST" action="/submit_oauth_key">
                <div class="form-group">
                    <label class="control-label" for "key">Key:</label>
                    <input id="oauth_key" class="input-large" name="oauth_key" type="text" placeholder="Google OAuth Key">
                </div>
                <div class="form-group">
                    <button type="submit" class="btn btn-primary">Login</button>
                </div>
            </form>
        </div>
</div>
