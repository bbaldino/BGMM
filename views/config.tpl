% include header.tpl {"session_status": session_status}
<div class="container">
    <div class="row">
        <div class="col-md-6 col-centered">
            <form class="form-horizontal well" name="watchpath_add" method="POST" action="/add_watch_path">
                <div class="form-group">
                    <label class="control-label" for="path">Add a new path:</label>
                    <input type="hidden" name="curr_page" value="/config">
                    <input id="path" class="input-large" name="path" type="text">
                </div>
                <div class="form-group">
                    <button type="submit" class="btn btn-primary">Add Path</button>
                    <button type="reset" class="btn">Cancel</button>
                </div>
            </form>
       </div>
    </div>
    <div class="row">
        <div class="col-md-6 col-centered">
            <form class="form-horizontal well" name="watchpath_remove" method="POST" action="/remove_watch_path">
                <div class="form-group">
                    <label class="control-label" for "watchpaths">Watched Paths</label>
                    <input type="hidden" name="curr_page" value="/config">
                    <select id="watchpaths" name="watchpaths" multiple="multiple">
                        % for watched_path in watched_paths:
                            <option value="{{watched_path}}">{{watched_path}}</option>
                        % end
                    </select>
                </div>
                <div class="form-group">
                    <button class="btn btn-primary" type="submit">Remove Path</button> 
                </div>
            </form>
        </div>
    </div>
</div>
