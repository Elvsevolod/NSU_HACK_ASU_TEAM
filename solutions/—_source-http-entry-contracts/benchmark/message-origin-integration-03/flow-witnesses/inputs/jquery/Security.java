import java.util.*;import java.util.stream.Collectors;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
class Profile implements UserDetails {
 String username;String password;boolean enabled;
 Profile(String name,String secret,boolean flag){username=name;password=secret;enabled=flag;}
 public String getUsername(){return username;}
 public String getPassword(){return password;}
 public boolean isAccountNonExpired(){return true;}
 public boolean isAccountNonLocked(){return true;}
 public boolean isCredentialsNonExpired(){return true;}
 public boolean isEnabled(){return enabled;}
 public List<SimpleGrantedAuthority> getAuthorities(){return Arrays.asList("ROLE_READER").stream().map(SimpleGrantedAuthority::new).collect(Collectors.toList());}
}
class Provider implements UserDetailsService {
 public UserDetails loadUserByUsername(String name){return new Profile(name,"{noop}secret",!name.equals("disabled"));}
}
class Config {UserDetailsService service;void configure(AuthenticationManagerBuilder builder){builder.userDetailsService(service);}}
class Api {AuthenticationManager manager;
 boolean entry(String name,String password){try{return manager.authenticate(new UsernamePasswordAuthenticationToken(name,password)).isAuthenticated();}
 catch(AuthenticationException failure){return false;}}
}