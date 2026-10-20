var mode=null;
          function loadSettings(){$.ajax({url:'/settings',type:'GET',success:function(reply){mode=reply.mode;}});}
          function publishSettings(){$.ajax({url:'/publish',type:'POST',data:{mode:mode}});}