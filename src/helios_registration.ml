open StdExtra
open Helios_datatypes_t
open Lwt

(* The following should be in configuration file... but
   <maxrequestbodysize> doesn't work *)
let () = Ocsigen_config.set_maxrequestbodysizeinmemory 32768

let elections_table = Ocsipersist.open_table "elections"

let () =
  let dir = ref None in
  let open Ocsigen_extensions.Configuration in
  Eliom_config.parse_config [
    element
      ~name:"load"
      ~obligatory:false
      ~attributes:[
        attribute ~name:"dir" ~obligatory:true (fun s -> dir := Some s);
      ]
      ()
  ];
  match !dir with
    | Some dir ->
      Ocsigen_messages.debug
        (fun () -> "Loading elections from " ^ dir ^ "...");
      Common.load_elections_and_votes dir |>
      Lwt_stream.iter_s (fun (e, votes, voters) ->
        let uuid = Uuidm.to_string e.Common.election.e_uuid in
        Ocsigen_messages.debug
          (fun () -> Printf.sprintf "-- loading %s (%s)" uuid e.Common.election.e_short_name);
        lwt () = Ocsipersist.add elections_table uuid e in
        let uuid_underscored = String.map (function '-' -> '_' | c -> c) uuid in
        let table = Ocsipersist.open_table ("votes_" ^ uuid_underscored) in
        let voters_table = Ocsipersist.open_table ("voters_" ^ uuid_underscored) in
        lwt () = Lwt_stream.iter_s (fun v ->
          Ocsipersist.add table (Common.hash_vote v) v
        ) votes in
        lwt () = Lwt_stream.iter_s (fun v ->
          Ocsipersist.add voters_table (Common.hash_user v.voter_user) v
        ) voters in
        return ()
      ) |>
      Lwt_main.run
    | None -> ()

let get_election_by_uuid x =
  try_lwt
    Ocsipersist.find elections_table (Uuidm.to_string x)
  with Not_found ->
    raise_lwt Eliom_common.Eliom_404

let get_featured_elections () =
  (* FIXME: doesn't scale when there are a lot of unfeatured elections *)
  Ocsipersist.fold_step (fun uuid e res ->
    let res = if e.Common.public_data.featured_p then e::res else res in
    return res
  ) elections_table []

let forbidden () = raise_lwt (
  Ocsigen_extensions.Ocsigen_http_error (
    Ocsigen_cookies.empty_cookieset, 403
  )
)

let if_eligible f uuid x =
  lwt election = get_election_by_uuid uuid in
  lwt user = Eliom_reference.get Helios_services.user in
  lwt () =
    if election.Common.public_data.private_p then (
      match user with
        | Some (_, user) ->
          lwt eligible = Helios_services.is_eligible uuid user in
          if not eligible then forbidden () else return ()
        | None -> forbidden ()
    ) else return ()
  in f uuid election user x

let () = Eliom_registration.Html5.register
  ~service:Helios_services.home
  (fun () () ->
    lwt featured = get_featured_elections () in
    Helios_templates.index ~featured)

let () = Eliom_registration.Html5.register
  ~service:Helios_services.login
  (fun () () ->
    (* FIXME *)
    let service = Helios_services.perform_login () in
    let () = Eliom_registration.Redirection.register
      ~service
      ~scope:Eliom_common.default_session_scope
      (fun () (user_name, admin_p) ->
        let user_type = "dummy" in
        Eliom_reference.set Helios_services.user
          (Some (admin_p, {user_name; user_type})) >>
        return Helios_services.home)
    in
    Helios_templates.dummy_login ~service)

let () = Eliom_registration.Redirection.register
  ~service:Helios_services.logout
  (fun () () ->
    Eliom_state.discard ~scope:Eliom_common.default_session_scope () >>
    return Helios_services.home)

let () = Eliom_registration.String.register
  ~service:Helios_services.election_raw
  (if_eligible
     (fun uuid election user () ->
       return (election.Common.raw, "application/json")
     )
  )

let () = Eliom_registration.String.register
  ~service:Helios_services.election_public_data
  (if_eligible
     (fun uuid election user () ->
       return (
         Helios_datatypes_j.string_of_election_public_data
           Core_datatypes_j.write_number
           election.Common.public_data,
         "application/json"
       )
     )
  )

let () = Eliom_registration.String.register
  ~service:Helios_services.election_ballots
  (if_eligible
     (fun uuid election user () ->
       let uuid_underscored = String.map (function '-' -> '_' | c -> c) (Uuidm.to_string uuid) in
       let table = Ocsipersist.open_table ("votes_" ^ uuid_underscored) in
       lwt ballots = Ocsipersist.fold_step (fun hash v res ->
         let s = Helios_datatypes_j.string_of_vote Core_datatypes_j.write_number v ^ "\n" in
         return (s :: res)
       ) table [] in
       let result = String.concat "" ballots in
       return (result, "application/json")
     )
  )

let () = Eliom_registration.String.register
  ~service:Helios_services.get_randomness
  (fun () () ->
    (* FIXME: DoS/entropy exhaustion vulnerability *)
    Lwt_preemptive.detach (fun () -> Cryptokit.Random.(string secure_rng 32)) () >>=
    wrap1 Cryptokit.(transform_string (Base64.encode_compact ())) >>=
    (fun x -> return (Helios_datatypes_j.string_of_randomness { randomness=x })) >>=
    (fun x -> return (x, "application/json"))
  )

let () = Eliom_registration.Html5.register
  ~service:Helios_services.election_view
  (if_eligible
     (fun uuid election user () ->
       Helios_templates.election_view ~election ~user
     )
  )

let () = Eliom_registration.Redirection.register
  ~service:Helios_services.election_vote
  (if_eligible
     (fun uuid election user () ->
       return (Helios_services.make_booth uuid)
     )
  )

let () = Eliom_registration.Redirection.register
  ~service:Helios_services.election_cast
  (if_eligible
     (fun uuid election user () ->
       return (
         Helios_services.(preapply_uuid election_view election)
       )
     )
  )

let () = Eliom_registration.Html5.register
  ~service:Helios_services.election_cast_post
  (if_eligible
     (fun uuid election user evote ->
       let result =
         try
           let vote = Helios_datatypes_j.vote_of_string Core_datatypes_j.read_number evote in
           let {g; p; q; y} = election.Common.election.e_public_key in
           let module G = (val ElGamal.make_ff_msubgroup p q g : ElGamal.GROUP with type t = Z.t) in
           let module Crypto = ElGamal.Make (G) in
           if
             Uuidm.equal uuid vote.election_uuid &&
             Crypto.verify_vote election.Common.election election.Common.fingerprint vote
           then `Valid (Common.hash_vote vote)
           else `Invalid
         with e -> `Malformed
       in
       Helios_templates.vote_cast ~election ~result
     )
  )
