import io.jsonwebtoken.*;import java.util.*;
 import org.springframework.http.*;import org.springframework.web.bind.annotation.*;
 import org.springframework.security.authentication.*;import org.springframework.security.core.*;
 import org.springframework.web.filter.OncePerRequestFilter;import javax.servlet.*;import javax.servlet.http.*;
 class Credentials{public String username;public String password;}
 class SessionToken{public String token;public String name;}
 class Login {AuthenticationManager manager;
  @PostMapping("/login") ResponseEntity<SessionToken> login(@RequestBody Credentials input){
   try{Authentication authenticated=manager.authenticate(new UsernamePasswordAuthenticationToken(input.username,input.password));
    Claims claims=Jwts.claims().setSubject(authenticated.getName());claims.put("roles",Arrays.asList("reader"));
    String token=Jwts.builder().setClaims(claims).setIssuedAt(new Date()).setExpiration(new Date(new Date().getTime()+60000L))
       .signWith(SignatureAlgorithm.HS256,"c2VjcmV0").compact();
    SessionToken result=new SessionToken();result.token=token;result.name=authenticated.getName();return ResponseEntity.ok(result);
   }catch(AuthenticationException failure){return new ResponseEntity<SessionToken>(null,HttpStatus.UNAUTHORIZED);}}
  @GetMapping("/protected") String read(){return "protected-data";}
 }
 class Gate extends OncePerRequestFilter {
  void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain){
   if(req.getRequestURI().equals("/protected")){
    String header=req.getHeader("Authorization");if(header==null){res.setStatus(401);return;}
    try{Claims claims=Jwts.parser().setSigningKey("c2VjcmV0").parseClaimsJws(header.substring(7)).getBody();
     if(!claims.getSubject().equals("alice")){res.setStatus(403);return;}}
    catch(JwtException failure){res.setStatus(401);return;}
   }chain.doFilter(req,res);
  }
 }